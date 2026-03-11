import os, re, json, time, requests
import frappe
from frappe.utils.file_manager import get_file_path

API_VERSION = "2024-11-30"
MODEL_ID    = "prebuilt-idDocument"
MODEL_READ  = "prebuilt-idDocument"

def _ensure_field(dt, fieldname):
    """Skip setting a field that doesn't exist on this doctype."""
    return frappe.db.has_column(dt, fieldname)

@frappe.whitelist()
def create_customer_from_scan(file_url: str, use_urlsource: int = 0, set_docname_to_name: int = 1, debug: int = 0):
    """
    1) Sends image/PDF to Azure (ID -> Read fallback)
    2) Maps to your Customer fields
    3) Creates & saves the Customer
    4) Sets appropriate attach/image fields for that doc type
    5) Attaches original file
    """
    frappe.only_for(("System Manager","Sales Manager","Sales User","Administrator"))

    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing in site_config.json")

    # Prepare input (private files => bytes; public URLs => urlSource)
    url_source, file_bytes = None, None
    if int(use_urlsource) and file_url.lower().startswith(("http://", "https://")):
        url_source = file_url
    else:
        path = get_file_path(file_url)
        if not os.path.exists(path):
            raise frappe.ValidationError(f"File not found: {path}")
        with open(path, "rb") as f:
            file_bytes = f.read()

    # --- Analyze with prebuilt-id then fallback to prebuilt-read ---
    mapped = {}
    try:
        op = _post_analyze(endpoint, key, MODEL_ID, url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_prebuilt_id(res) or {}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"prebuilt-id failed: {e}", "Azure DI create_customer_from_scan")

    if not mapped.get("customer_name") and not any(mapped.get(k) for k in ("passport_number","license_number","id_number")):
        # Fallback: prebuilt-read
        op = _post_analyze(endpoint, key, MODEL_READ, url_source=url_source, file_bytes=file_bytes, overload="analyzeDocument")
        res = _poll(op, key)
        if res.get("status") != "succeeded":
            raise frappe.ValidationError("Azure reading failed")
        text = _read_text(res)
        if int(debug):
            blob = text[:3000] + ("…" if len(text) > 3000 else "")
            frappe.log_error(blob, "Azure Read – raw text (create)")
        mapped = _map_read_text(text) or {}

    # --- Build Customer doc payload ---
    # Ensure Date fields are YYYY-MM-DD
    def iso(v): return _norm_date(v) if isinstance(v, str) else v

    customer_name = mapped.get("customer_name") or "New Customer"
    doc_type = mapped.get("doc_type") or "passport"

    payload = {
        "doctype": "Customer",
        "customer_type": "Individual",
        "customer_name": customer_name,
        # common
        "date_of_birth": iso(mapped.get("date_of_birth")) or None,
        # passport set
        "passport_number": mapped.get("passport_number") or None,
        "passport_expiry": iso(mapped.get("passport_expiry")) or None,
        # license set
        "license_number": mapped.get("license_number") or None,
        "license_expiry": iso(mapped.get("license_expiry")) or None,
        "driving_license": mapped.get("driving_license") or None,
        # national id set
        "id_number": mapped.get("id_number") or None,
        "id_expiry": iso(mapped.get("id_expiry")) or None,
        "national_id": mapped.get("national_id") or None,
    }

    # attach/image fields per doc type (only if fields exist)
    image_map = {
        "passport":   [("attach_passport", "passport_image")],
        "driving_license": [("attach_license", "license_image")],
        "national_id":     [("attach_id", "id_image")]
    }
    for attach_fn, image_fn in image_map.get(doc_type, []):
        if _ensure_field("Customer", attach_fn):
            payload[attach_fn] = file_url
        if _ensure_field("Customer", image_fn):
            payload[image_fn] = file_url

    # Prune None/empty
    payload = {k: v for k, v in payload.items() if v not in (None, "", [])}

    # --- Create Customer ---
    customer = frappe.get_doc(payload).insert(ignore_permissions=False)
    created_name = customer.name

    # --- Attach original file for audit ---
    try:
        f = frappe.new_doc("File")
        f.file_url = file_url
        f.attached_to_doctype = "Customer"
        f.attached_to_name = created_name
        f.insert(ignore_permissions=True)
    except Exception as e:
        if int(debug):
            frappe.log_error(f"Attach failed: {e}", "create_customer_from_scan")

    # --- Optional: rename docname to customer_name (if requested + no conflict) ---
    if int(set_docname_to_name) and customer_name and customer_name != created_name:
        # Only if you configured autoname by field: if not, we can still rename safely if no collision
        if not frappe.db.exists("Customer", customer_name):
            try:
                frappe.rename_doc("Customer", created_name, customer_name, force=True)
                created_name = customer_name
            except Exception as e:
                if int(debug):
                    frappe.log_error(f"Rename failed: {e}", "create_customer_from_scan")

    return {"name": created_name, "doc_type": doc_type, "customer_name": customer_name}

def _cfg():
    """Get Azure DI credentials. Priority: Settings DocType > site_config (fallback)"""
    try:
        if frappe.db.exists("Azure Document Intelligence Settings", "Azure Document Intelligence Settings"):
            settings = frappe.get_single("Azure Document Intelligence Settings")
            if settings.enabled and settings.endpoint and settings.api_key:
                return settings.endpoint.rstrip('/'), settings.get_password("api_key")
    except Exception as e:
        frappe.log_error(f"Error reading Azure DI Settings: {e}", "Azure DI Config")

    # Fallback to site_config
    sc = frappe.get_site_config()
    endpoint = sc.get("azure_di_endpoint")
    key = sc.get("azure_di_key")

    if not (endpoint and key):
        frappe.throw("Azure Document Intelligence not configured. Please configure in Settings or site_config.json")

    return endpoint.rstrip('/') if endpoint else None, key

def _post_analyze(endpoint, key, model, *, url_source=None, file_bytes=None, overload=None):
    base = f"{endpoint}/documentintelligence/documentModels/{model}:analyze"
    params = {"api-version": API_VERSION}
    if overload:
        params["_overload"] = overload
    headers = {"Ocp-Apim-Subscription-Key": key}
    if url_source:
        headers["Content-Type"] = "application/json"
        r = requests.post(base, params=params, headers=headers, json={"urlSource": url_source}, timeout=60)
    else:
        headers["Content-Type"] = "application/octet-stream"
        r = requests.post(base, params=params, headers=headers, data=file_bytes, timeout=60)
    r.raise_for_status()
    op_loc = r.headers.get("Operation-Location")
    if not op_loc:
        raise frappe.ValidationError("Azure did not return Operation-Location")
    return op_loc

def _poll(op_location, key, timeout_s=90):
    headers = {"Ocp-Apim-Subscription-Key": key}
    t0 = time.time()
    while True:
        rr = requests.get(op_location, headers=headers, timeout=60)
        rr.raise_for_status()
        j = rr.json()
        st = j.get("status")
        if st in ("succeeded","failed"):
            return j
        if time.time() - t0 > timeout_s:
            raise frappe.ValidationError("Azure analyze timed out")
        time.sleep(1)

def _read_text(res):
    ar = (res.get("analyzeResult") or {})
    paras = ar.get("paragraphs") or []
    if paras:
        return "\n".join([p.get("content","") for p in paras if p.get("content")]).strip()
    if isinstance(ar.get("content"), str) and ar["content"].strip():
        return ar["content"].strip()
    lines=[]
    for pg in ar.get("pages") or []:
        for ln in pg.get("lines", []):
            if ln.get("content"): lines.append(ln["content"])
    return "\n".join(lines).strip()

def _norm_date(s):
    if not s: return None
    s = s.replace(".", "/").replace("-", "/")
    parts = s.split("/")
    if len(parts) == 3:
        a,b,c = parts
        a,b,c = a.zfill(4 if len(a)==4 else 2), b.zfill(2), c.zfill(4)
        if len(a)==4:  # YYYY/MM/DD
            return f"{a}-{b}-{c}"
        return f"{c}-{b}-{a}"  # DD/MM/YYYY -> YYYY-MM-DD
    return None

def _map_prebuilt_id(res):
    """
    Map Azure prebuilt-id result to YOUR fields + doc_type.
    All dates -> dd-mm-yyyy for Frappe.
    """
    out = {k: None for k in [
        "id_expiry","id_number","license_expiry","license_number","date_of_birth",
        "passport_expiry","passport_number","national_id","driving_license",
        "customer_name"
    ]}
    out["doc_type"] = None

    docs = (res.get("analyzeResult") or {}).get("documents") or []
    if not docs:
        return out
    d = docs[0]
    fields = d.get("fields", {}) or {}

    def v(*keys):
        for k in keys:
            node = fields.get(k) or {}
            val = node.get("valueString") or node.get("content") or node.get("valueDate")
            if val: return str(val).strip()
        return None

    # docType e.g. idDocument.passport/driverLicense/nationalIdentityCard
    dt = (d.get("docType") or "").lower()
    if "passport" in dt: out["doc_type"] = "passport"
    elif "driver" in dt: out["doc_type"] = "driving_license"
    elif "identity" in dt or "idcard" in dt: out["doc_type"] = "national_id"

    # Names
    full  = v("FullName","Name")
    first = v("FirstName","GivenName","GivenNames","Forename")
    last  = v("LastName","Surname","FamilyName")
    out["customer_name"] = full or (f"{first or ''} {last or ''}".strip() or None)

    # DOB (normalize)
    dob_raw = v("DateOfBirth","BirthDate","DOB")
    out["date_of_birth"] = _norm_date(dob_raw)

    # Number / Expiry generic
    num = v("DocumentNumber","IDNumber","LicenseNumber","PersonalNumber","CardNumber","Number")
    exp_raw = v("DateOfExpiration","ExpirationDate","ExpiryDate","ValidUntil","ValidTo")
    exp = _norm_date(exp_raw)

    if out["doc_type"] == "passport":
        out["passport_number"] = num
        out["passport_expiry"] = exp
    elif out["doc_type"] == "driving_license":
        out["license_number"] = num
        out["license_expiry_scanned"] = exp
        out["driving_license"] = num
    elif out["doc_type"] == "national_id":
        out["id_number"] = num
        out["id_expiry"] = exp
        out["national_id"] = num

    return out

def _map_read_text(text):
    """
    Fallback regex mapping to YOUR fields + doc_type.
    All dates -> dd-mm-yyyy for Frappe.
    """
    out = {k: None for k in [
        "id_expiry","id_number","license_expiry","license_number","date_of_birth",
        "passport_expiry","passport_number","national_id","driving_license",
        "customer_name"
    ]}
    # Doc type hints
    dtype = "passport"
    if re.search(r"License", text, re.I): dtype = "driving_license"
    if re.search(r"\bID\b|\bEmirates\b|\bNational\b", text, re.I): dtype = "national_id"
    out["doc_type"] = dtype

    # Name
    m = re.search(r"(Full\s*Name|Name)\s*[:\-]\s*([A-Za-z' ]{3,})", text, re.I)
    if m:
        out["customer_name"] = m.group(2).strip()
    else:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        cand = [ln for ln in lines if ln.replace(" ","").isalpha() and len(ln.split())>=2 and ln.isupper()]
        if cand: out["customer_name"] = cand[0].title()

    # DOB -> dd-mm-yyyy
    DATE_RX = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    m = re.search(r"(DOB|Date\s*of\s*Birth)\s*[:\-]?\s*"+DATE_RX, text, re.I)
    if m:
        out["date_of_birth"] = _norm_date(m.group(2) if m.lastindex>=2 else m.group(1))

    # Number + Expiry (generic)
    mnum = re.search(r"(Passport|Document|ID|Card|License)\s*(No\.?|Number)\s*[:\-]?\s*([A-Z0-9\-]+)", text, re.I)
    if not mnum:
        mnum = re.search(r"\b([A-Z]\d{6,9})\b", text)
    generic_num = (mnum.group(3) if (mnum and mnum.lastindex and mnum.lastindex>=3) else (mnum.group(1) if mnum else None))

    mexp = re.search(r"(Expiry|Expiration|Exp\. Date|Valid\s*Until)\s*[:\-]?\s*"+DATE_RX, text, re.I)
    generic_exp = _norm_date(mexp.group(2) if (mexp and mexp.lastindex>=2) else (mexp.group(1) if mexp else None))

    if dtype == "passport":
        out["passport_number"] = generic_num
        out["passport_expiry"] = generic_exp
    elif dtype == "driving_license":
        out["license_number"] = generic_num
        out["license_expiry"] = generic_exp
        out["driving_license"] = generic_num
    elif dtype == "national_id":
        out["id_number"] = generic_num
        out["id_expiry"] = generic_exp
        out["national_id"] = generic_num

    return out

def _norm_date(s):
    """Return YYYY-MM-DD from inputs like YYYY/MM/DD, DD-MM-YYYY, etc."""
    if not s: return None
    s = s.replace(".", "/").replace("-", "/")
    parts = s.split("/")
    if len(parts) != 3: return None

    a, b, c = parts
    if len(a) == 4:   # YYYY/MM/DD
        yyyy, mm, dd = a, b.zfill(2), c.zfill(2)
    elif len(c) == 4: # DD/MM/YYYY
        yyyy, mm, dd = c, b.zfill(2), a.zfill(2)
    else:
        return None
    return f"{yyyy}-{mm}-{dd}"

@frappe.whitelist()
def analyze_scan(file_url: str, use_urlsource: int = 0, debug: int = 0):
    """
    NEW-FORM helper: analyze the scan and RETURN values mapped to your fields
    (no DB writes). The client script will set them on the unsaved form.
    """
    frappe.only_for(("System Manager","Sales Manager","Sales User","Administrator"))
    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing in site_config.json")

    # prepare input
    url_source = None; file_bytes = None
    if int(use_urlsource) and file_url.lower().startswith(("http://","https://")):
        url_source = file_url
    else:
        path = get_file_path(file_url)
        if not os.path.exists(path):
            raise frappe.ValidationError(f"File not found: {path}")
        with open(path, "rb") as f:
            file_bytes = f.read()

    # try prebuilt-id first
    try:
        op = _post_analyze(endpoint, key, MODEL_ID, url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_prebuilt_id(res)
        else:
            mapped = {}
    except Exception as e:
        mapped = {}
        if int(debug): frappe.log_error(f"prebuilt-id failed: {e}", "Azure ID")

    # fallback to prebuilt-read
    if not mapped.get("customer_name") and not any(mapped.get(k) for k in ("passport_number","license_number","id_number")):
        op = _post_analyze(endpoint, key, MODEL_READ, url_source=url_source, file_bytes=file_bytes, overload="analyzeDocument")
        res = _poll(op, key)
        if res.get("status") != "succeeded":
            raise frappe.ValidationError("Azure reading failed")
        text = _read_text(res)
        if int(debug):
            frappe.log_error((text[:3000] + ("…" if len(text) > 3000 else "")), "Azure Read – raw text")
        mapped = _map_read_text(text)

    # attach/image fields for the detected doc type (client will set if exists)
    mapped["doc_type"] = mapped.get("doc_type") or "passport"
    if mapped["doc_type"] == "passport":
        mapped["attach_passport"] = file_url
        mapped["passport_image"] = file_url
    elif mapped["doc_type"] == "driving_license":
        mapped["attach_license"] = file_url
        mapped["license_image"] = file_url
    elif mapped["doc_type"] == "national_id":
        mapped["attach_id"] = file_url
        mapped["id_image"] = file_url

    # ensure only your fields are returned
    allowed = {
        "id_expiry","id_number","license_expiry","license_number","date_of_birth",
        "passport_expiry","passport_number","attach_id","id_image","national_id",
        "attach_license","license_image","driving_license","attach_passport",
        "passport_image","customer_name","doc_type"
    }
    filtered = {k: v for k, v in mapped.items() if k in allowed and v}

    if int(debug):
        frappe.log_error(json.dumps({"doc_type": mapped.get("doc_type"), "returned": filtered}, indent=2), "Analyze Scan – mapped")

    return {"fields": filtered, "doc_type": mapped.get("doc_type")}


# ==================== COMPANY DOCUMENT SCANNING FUNCTIONS ====================

@frappe.whitelist()
def scan_credit_application(file_url: str, use_urlsource: int = 0, debug: int = 0):
    """
    Scan Credit Application form using Azure Document Intelligence
    Returns: credit_application_number, credit_limit_approved, credit_application_expiry
    """
    frappe.only_for(("System Manager","Sales Manager","Sales User","Administrator"))
    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing")

    url_source, file_bytes = _prepare_file_input(file_url, int(use_urlsource))

    # Try prebuilt-layout model for business forms
    try:
        op = _post_analyze(endpoint, key, "prebuilt-layout", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_credit_application(res)
            if mapped.get("credit_application_number") or mapped.get("credit_limit_approved"):
                if int(debug):
                    frappe.log_error(json.dumps(mapped, indent=2), "Credit Application - Structured")
                return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"prebuilt-document failed: {e}", "Credit Application Scan")

    # Fallback to text extraction
    try:
        op = _post_analyze(endpoint, key, "prebuilt-read", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            text = _read_text(res)
            if int(debug):
                frappe.log_error((text[:3000] + ("…" if len(text) > 3000 else "")), "Credit Application - Text")
            mapped = _map_credit_application_text(text)
            return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"Text extraction failed: {e}", "Credit Application Scan")
        raise frappe.ValidationError("Failed to scan credit application")


@frappe.whitelist()
def scan_trn_certificate(file_url: str, use_urlsource: int = 0, debug: int = 0):
    """
    Scan TRN Certificate using Azure Document Intelligence
    Returns: trn_number, trn_certificate_expiry
    """
    frappe.only_for(("System Manager","Sales Manager","Sales User","Administrator"))
    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing")

    url_source, file_bytes = _prepare_file_input(file_url, int(use_urlsource))

    # Try prebuilt-layout model
    try:
        op = _post_analyze(endpoint, key, "prebuilt-layout", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_trn_certificate(res)
            if mapped.get("trn_number"):
                if int(debug):
                    frappe.log_error(json.dumps(mapped, indent=2), "TRN Certificate - Structured")
                return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"prebuilt-document failed: {e}", "TRN Certificate Scan")

    # Fallback to text extraction
    try:
        op = _post_analyze(endpoint, key, "prebuilt-read", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            text = _read_text(res)
            if int(debug):
                frappe.log_error((text[:3000] + ("…" if len(text) > 3000 else "")), "TRN Certificate - Text")
            mapped = _map_trn_certificate_text(text)
            return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"Text extraction failed: {e}", "TRN Certificate Scan")
        raise frappe.ValidationError("Failed to scan TRN certificate")


@frappe.whitelist()
def scan_trade_license(file_url: str, use_urlsource: int = 0, debug: int = 0):
    """
    Scan Trade License using Azure Document Intelligence
    Returns: trade_license_number, trade_license_expiry
    """
    frappe.only_for(("System Manager","Sales Manager","Sales User","Administrator"))
    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing")

    url_source, file_bytes = _prepare_file_input(file_url, int(use_urlsource))

    # Try prebuilt-layout model
    mapped = {}
    try:
        op = _post_analyze(endpoint, key, "prebuilt-layout", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_trade_license(res)
            # Always log for debugging
            frappe.log_error(json.dumps({"method": "prebuilt-layout", "mapped": mapped}, indent=2), "Trade License Scan Debug")
            if mapped.get("trade_license_number") or mapped.get("trade_license_expiry"):
                return {"fields": mapped}
    except Exception as e:
        frappe.log_error(f"prebuilt-layout failed: {str(e)}", "Trade License Scan Error")

    # Fallback to text extraction
    try:
        op = _post_analyze(endpoint, key, "prebuilt-read", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            text = _read_text(res)
            # Always log extracted text for debugging
            frappe.log_error((text[:3000] + ("…" if len(text) > 3000 else "")), "Trade License - Extracted Text")
            mapped = _map_trade_license_text(text)
            frappe.log_error(json.dumps({"method": "text-fallback", "mapped": mapped}, indent=2), "Trade License Text Mapping")
            return {"fields": mapped}
    except Exception as e:
        frappe.log_error(f"Text extraction failed: {str(e)}", "Trade License Scan Error")
        raise frappe.ValidationError("Failed to scan trade license")


# ==================== HELPER FUNCTIONS ====================

def _prepare_file_input(file_url, use_urlsource):
    """Prepare file input for Azure API - returns (url_source, file_bytes)"""
    url_source, file_bytes = None, None
    if use_urlsource and file_url.lower().startswith(("http://", "https://")):
        url_source = file_url
    else:
        path = get_file_path(file_url)
        if not os.path.exists(path):
            raise frappe.ValidationError(f"File not found: {path}")
        with open(path, "rb") as f:
            file_bytes = f.read()
    return url_source, file_bytes


# ==================== STRUCTURED MAPPING FUNCTIONS ====================

def _map_credit_application(res):
    """Map Azure prebuilt-layout result for Credit Application"""
    out = {
        "credit_application_number": None,
        "credit_limit_approved": None,
        "credit_application_expiry": None
    }

    ar = res.get("analyzeResult") or {}

    # First, try documents.fields structure
    documents = ar.get("documents") or []
    for doc in documents:
        fields = doc.get("fields") or {}

        # Check all fields for relevant data
        for field_name, field_value in fields.items():
            field_name_lower = field_name.lower()
            content = field_value.get("content", "")

            if not content:
                continue

            # Application number
            if not out["credit_application_number"] and any(term in field_name_lower for term in ["application", "reference", "number"]):
                out["credit_application_number"] = content.strip()

            # Credit limit / Amount
            if not out["credit_limit_approved"] and any(term in field_name_lower for term in ["credit", "limit", "amount"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", content.replace(",", ""))
                if amt:
                    out["credit_limit_approved"] = float(amt.group().replace(",", ""))

            # Expiry date
            if not out["credit_application_expiry"] and any(term in field_name_lower for term in ["expiry", "expiration", "valid"]):
                normalized = _norm_date(content)
                if normalized:
                    out["credit_application_expiry"] = normalized

    # Fallback to key-value pairs
    if not all([out["credit_application_number"], out["credit_limit_approved"], out["credit_application_expiry"]]):
        kv_pairs = ar.get("keyValuePairs") or []
        for pair in kv_pairs:
            key_content = (pair.get("key") or {}).get("content", "").lower()
            value_content = (pair.get("value") or {}).get("content", "")

            if not value_content:
                continue

            if not out["credit_application_number"] and any(term in key_content for term in ["application", "reference", "app no", "credit no", "number"]):
                if re.search(r"[A-Z0-9]{4,}", value_content):
                    out["credit_application_number"] = value_content.strip()

            if not out["credit_limit_approved"] and any(term in key_content for term in ["credit limit", "approved limit", "limit approved", "amount"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", value_content.replace(",", ""))
                if amt:
                    out["credit_limit_approved"] = float(amt.group().replace(",", ""))

            if not out["credit_application_expiry"] and any(term in key_content for term in ["expiry", "expiration", "valid until", "valid till"]):
                out["credit_application_expiry"] = _norm_date(value_content)

    return out


def _map_trn_certificate(res):
    """Map Azure prebuilt-layout result for TRN Certificate"""
    out = {
        "trn_number": None,
        "trn_certificate_expiry": None
    }

    ar = res.get("analyzeResult") or {}

    # First, try to extract from documents.fields (prebuilt-layout structure)
    documents = ar.get("documents") or []
    for doc in documents:
        fields = doc.get("fields") or {}

        # Look for TaxRegistrationNumber or TRN field (Azure's potential field names)
        if "TaxRegistrationNumber" in fields:
            trn_field = fields["TaxRegistrationNumber"]
            if trn_field.get("content"):
                trn_content = trn_field["content"].replace(" ", "")
                trn_match = re.search(r"\d{15}", trn_content)
                if trn_match:
                    out["trn_number"] = trn_match.group()
                    frappe.log_error(f"Found TaxRegistrationNumber: {out['trn_number']}", "TRN Certificate Mapping")

        # Look for ExpiryDate field (Azure's standard field name)
        if "ExpiryDate" in fields:
            expiry = fields["ExpiryDate"]
            if expiry.get("content"):
                out["trn_certificate_expiry"] = _norm_date(expiry["content"])
                frappe.log_error(f"Found ExpiryDate: {expiry['content']} -> {out['trn_certificate_expiry']}", "TRN Certificate Mapping")

        # Also check common variations in field names
        for field_name, field_value in fields.items():
            field_name_lower = field_name.lower()
            content = field_value.get("content", "")

            if not content:
                continue

            # TRN number variations
            if not out["trn_number"] and any(term in field_name_lower for term in ["trn", "tax", "registration", "number"]):
                trn_match = re.search(r"\d{15}", content.replace(" ", ""))
                if trn_match:
                    out["trn_number"] = trn_match.group()
                    frappe.log_error(f"Found TRN via field {field_name}: {content} -> {out['trn_number']}", "TRN Certificate Mapping")

            # Expiry date variations
            if not out["trn_certificate_expiry"] and any(term in field_name_lower for term in ["expiry", "expiration", "expire", "valid"]):
                normalized = _norm_date(content)
                if normalized:
                    out["trn_certificate_expiry"] = normalized
                    frappe.log_error(f"Found expiry via field {field_name}: {content} -> {normalized}", "TRN Certificate Mapping")

    # If not found in documents, try key-value pairs (fallback)
    if not out["trn_number"] or not out["trn_certificate_expiry"]:
        kv_pairs = ar.get("keyValuePairs") or []
        for pair in kv_pairs:
            key_content = (pair.get("key") or {}).get("content", "").lower()
            value_content = (pair.get("value") or {}).get("content", "")

            if not value_content:
                continue

            # TRN number (15 digits in UAE)
            if not out["trn_number"] and any(term in key_content for term in ["trn", "tax", "registration", "number"]):
                trn_match = re.search(r"\d{15}", value_content.replace(" ", ""))
                if trn_match:
                    out["trn_number"] = trn_match.group()

            # Expiry date
            if not out["trn_certificate_expiry"] and any(term in key_content for term in ["expiry", "expiration", "valid until", "valid till"]):
                normalized = _norm_date(value_content)
                if normalized:
                    out["trn_certificate_expiry"] = normalized

    return out


def _map_trade_license(res):
    """Map Azure prebuilt-layout result for Trade License"""
    out = {
        "trade_license_number": None,
        "trade_license_expiry": None
    }

    ar = res.get("analyzeResult") or {}

    # First, try to extract from documents.fields (prebuilt-layout structure)
    documents = ar.get("documents") or []
    for doc in documents:
        fields = doc.get("fields") or {}

        # Look for MainLicenseNumber field (Azure's standard field name)
        if "MainLicenseNumber" in fields:
            main_lic = fields["MainLicenseNumber"]
            if main_lic.get("content"):
                out["trade_license_number"] = main_lic["content"].strip()
                frappe.log_error(f"Found MainLicenseNumber: {out['trade_license_number']}", "Trade License Mapping")

        # Look for ExpiryDate field (Azure's standard field name)
        if "ExpiryDate" in fields:
            expiry = fields["ExpiryDate"]
            if expiry.get("content"):
                out["trade_license_expiry"] = _norm_date(expiry["content"])
                frappe.log_error(f"Found ExpiryDate: {expiry['content']} -> {out['trade_license_expiry']}", "Trade License Mapping")

        # Also check common variations in field names
        for field_name, field_value in fields.items():
            field_name_lower = field_name.lower()
            content = field_value.get("content", "")

            if not content:
                continue

            # License number variations
            if not out["trade_license_number"] and any(term in field_name_lower for term in ["license", "licence", "number", "registration"]):
                out["trade_license_number"] = content.strip()
                frappe.log_error(f"Found license via field {field_name}: {content}", "Trade License Mapping")

            # Expiry date variations
            if not out["trade_license_expiry"] and any(term in field_name_lower for term in ["expiry", "expiration", "expire", "valid"]):
                normalized = _norm_date(content)
                if normalized:
                    out["trade_license_expiry"] = normalized
                    frappe.log_error(f"Found expiry via field {field_name}: {content} -> {normalized}", "Trade License Mapping")

    # If not found in documents, try key-value pairs (fallback)
    if not out["trade_license_number"] or not out["trade_license_expiry"]:
        kv_pairs = ar.get("keyValuePairs") or []
        for pair in kv_pairs:
            key_content = (pair.get("key") or {}).get("content", "").lower()
            value_content = (pair.get("value") or {}).get("content", "")

            if not value_content:
                continue

            # License number
            if not out["trade_license_number"] and any(term in key_content for term in ["license", "licence", "number", "registration", "permit"]):
                out["trade_license_number"] = value_content.strip()

            # Expiry date
            if not out["trade_license_expiry"] and any(term in key_content for term in ["expiry", "expiration", "expire", "valid", "end date"]):
                normalized = _norm_date(value_content)
                if normalized:
                    out["trade_license_expiry"] = normalized

    return out


# ==================== TEXT-BASED MAPPING FUNCTIONS (FALLBACK) ====================

def _map_credit_application_text(text):
    """Fallback regex mapping for Credit Application from raw text"""
    out = {
        "credit_application_number": None,
        "credit_limit_approved": None,
        "credit_application_expiry": None
    }

    # Application number - look for patterns like "App No: ABC123" or "Reference: XYZ789"
    app_patterns = [
        r"(?:Application|Reference|App|Credit)\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9\-/]{4,})",
        r"\b([A-Z]{2,}\d{4,}|\d{4,}[A-Z]{2,})\b"  # Alphanumeric codes
    ]
    for pattern in app_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["credit_application_number"] = m.group(1).strip()
            break

    # Credit limit - look for currency amounts
    limit_patterns = [
        r"(?:Credit\s*Limit|Approved\s*Limit|Limit\s*Approved|Amount)\s*[:\-]?\s*(?:AED|USD|SAR)?\s*([\d,]+(?:\.\d{2})?)",
        r"(?:AED|USD|SAR)\s*([\d,]+(?:\.\d{2})?)"
    ]
    for pattern in limit_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["credit_limit_approved"] = float(m.group(1).replace(",", ""))
            break

    # Expiry date
    DATE_RX = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    m = re.search(r"(?:Expiry|Expiration|Valid\s*Until|Valid\s*Till)\s*[:\-]?\s*" + DATE_RX, text, re.I)
    if m:
        out["credit_application_expiry"] = _norm_date(m.group(1))

    return out


def _map_trn_certificate_text(text):
    """Fallback regex mapping for TRN Certificate from raw text"""
    out = {
        "trn_number": None,
        "trn_certificate_expiry": None
    }

    # TRN number (15 digits in UAE)
    trn_patterns = [
        r"(?:TRN|Tax\s*Registration\s*Number)\s*[:\-]?\s*(\d{15})",
        r"\b(\d{15})\b"  # 15-digit standalone number
    ]
    for pattern in trn_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["trn_number"] = m.group(1)
            break

    # Expiry date
    DATE_RX = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    m = re.search(r"(?:Expiry|Expiration|Valid\s*Until|Valid\s*Till)\s*[:\-]?\s*" + DATE_RX, text, re.I)
    if m:
        out["trn_certificate_expiry"] = _norm_date(m.group(1))

    return out


def _map_trade_license_text(text):
    """Fallback regex mapping for Trade License from raw text"""
    out = {
        "trade_license_number": None,
        "trade_license_expiry": None
    }

    # License number - look for patterns (more flexible)
    lic_patterns = [
        # Pattern 1: "License No: 123456" or "License Number: CN-123456"
        r"(?:Trade\s*License|License|Licence|Permit|Certificate)\s*(?:No\.?|Number|#|:)\s*[:\-]?\s*([A-Z0-9\.\-/\s]{3,25})",
        # Pattern 2: "Registration No: DED/123/2024"
        r"(?:Registration|Reg\.?|DED)\s*(?:No\.?|Number|#|:)\s*[:\-]?\s*([A-Z0-9\.\-/\s]{3,25})",
        # Pattern 3: Look for common UAE formats (CN-xxxxxxx, DED/xxx/xxxx, etc.)
        r"\b(CN[\-\s]?\d{5,10})\b",
        r"\b(DED[/\-\s]?\d+[/\-\s]?\d+)\b",
        # Pattern 4: Standalone alphanumeric with dashes/slashes (fallback)
        r"\b([A-Z]{2,5}[\-/]?\d{5,10})\b"
    ]

    for pattern in lic_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            license_num = m.group(1).strip()
            # Filter out common false positives
            if len(license_num) >= 3 and license_num not in ['P.O', 'TEL', 'FAX', 'BOX']:
                out["trade_license_number"] = license_num
                break

    # Expiry date - multiple patterns
    DATE_RX = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
    expiry_patterns = [
        r"(?:Expiry|Expiration|Expire\s*Date|Expires)\s*[:\-]?\s*" + DATE_RX,
        r"(?:Valid\s*Until|Valid\s*Till|Valid\s*To|Validity)\s*[:\-]?\s*" + DATE_RX,
        r"(?:End\s*Date|End)\s*[:\-]?\s*" + DATE_RX,
        r"(?:Date\s*of\s*Expiry)\s*[:\-]?\s*" + DATE_RX
    ]

    for pattern in expiry_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            # Get the date group (might be group 1 or 2 depending on pattern)
            date_str = m.group(1) if m.lastindex >= 1 else None
            if date_str:
                normalized = _norm_date(date_str)
                if normalized:
                    out["trade_license_expiry"] = normalized
                    break

    return out


# ==================== INSURANCE POLICY SCANNING ====================

@frappe.whitelist()
def scan_insurance_policy(file_url: str, use_urlsource: int = 0, debug: int = 0):
    """
    Scan Insurance Policy document using Azure Document Intelligence
    Returns: policy_number, insurance_provider, insured_name, policy_start_date,
             insurance_expiry, premium_amount, coverage_type, sum_insured,
             policy_conditions (array)
    """
    frappe.only_for(("System Manager","Fleet Manager","Right Hire Admin","Administrator"))
    endpoint, key = _cfg()
    if not (endpoint and key):
        raise frappe.ValidationError("Azure endpoint/key missing")

    url_source, file_bytes = _prepare_file_input(file_url, int(use_urlsource))

    # Try prebuilt-layout model first
    mapped = {}
    try:
        op = _post_analyze(endpoint, key, "prebuilt-layout", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            mapped = _map_insurance_policy(res)
            if int(debug):
                frappe.log_error(json.dumps({"method": "prebuilt-layout", "mapped": mapped}, indent=2), "Insurance Policy Scan Debug")
            if mapped.get("policy_number") or mapped.get("insurance_provider"):
                return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"prebuilt-layout failed: {str(e)}", "Insurance Policy Scan Error")

    # Fallback to text extraction
    try:
        op = _post_analyze(endpoint, key, "prebuilt-read", url_source=url_source, file_bytes=file_bytes)
        res = _poll(op, key)
        if res.get("status") == "succeeded":
            text = _read_text(res)
            if int(debug):
                frappe.log_error((text[:3000] + ("…" if len(text) > 3000 else "")), "Insurance Policy - Extracted Text")
            mapped = _map_insurance_policy_text(text)
            if int(debug):
                frappe.log_error(json.dumps({"method": "text-fallback", "mapped": mapped}, indent=2), "Insurance Policy Text Mapping")
            return {"fields": mapped}
    except Exception as e:
        if int(debug):
            frappe.log_error(f"Text extraction failed: {str(e)}", "Insurance Policy Scan Error")
        raise frappe.ValidationError("Failed to scan insurance policy")


def _map_insurance_policy(res):
    """Map Azure prebuilt-layout result for Insurance Policy"""
    out = {
        "policy_number": None,
        "insurance_provider": None,
        "insured_name": None,
        "policy_start_date": None,
        "insurance_expiry": None,
        "premium_amount": None,
        "coverage_type": None,
        "sum_insured": None,
        "policy_conditions": []
    }

    ar = res.get("analyzeResult") or {}

    # Try to extract from documents.fields (prebuilt-layout structure)
    documents = ar.get("documents") or []
    for doc in documents:
        fields = doc.get("fields") or {}

        # Check all fields for relevant insurance data
        for field_name, field_value in fields.items():
            field_name_lower = field_name.lower()
            content = field_value.get("content", "")

            if not content:
                continue

            # Policy number
            if not out["policy_number"] and any(term in field_name_lower for term in ["policy", "number", "certificate"]):
                # Look for alphanumeric policy number pattern
                policy_match = re.search(r"[A-Z0-9]{5,}", content.replace(" ", ""))
                if policy_match:
                    out["policy_number"] = policy_match.group()

            # Insurance provider / Company name
            if not out["insurance_provider"] and any(term in field_name_lower for term in ["insurer", "provider", "company", "underwriter"]):
                out["insurance_provider"] = content.strip()

            # Insured name
            if not out["insured_name"] and any(term in field_name_lower for term in ["insured", "policyholder", "owner", "name"]):
                # Skip if it's a company name or provider
                if "company" not in content.lower() and "insurance" not in content.lower():
                    out["insured_name"] = content.strip()

            # Premium amount
            if not out["premium_amount"] and any(term in field_name_lower for term in ["premium", "amount", "cost", "fee"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", content.replace(",", ""))
                if amt:
                    out["premium_amount"] = float(amt.group().replace(",", ""))

            # Sum insured / Vehicle value
            if not out["sum_insured"] and any(term in field_name_lower for term in ["sum", "insured", "value", "vehicle value", "market value"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", content.replace(",", ""))
                if amt:
                    out["sum_insured"] = float(amt.group().replace(",", ""))

            # Coverage type
            if not out["coverage_type"] and any(term in field_name_lower for term in ["coverage", "type", "plan", "package"]):
                content_lower = content.lower()
                if "comprehensive" in content_lower:
                    out["coverage_type"] = "Comprehensive"
                elif "third party" in content_lower:
                    if "fire" in content_lower or "theft" in content_lower:
                        out["coverage_type"] = "Third Party Fire & Theft"
                    else:
                        out["coverage_type"] = "Third Party"

            # Policy start date
            if not out["policy_start_date"] and any(term in field_name_lower for term in ["start", "effective", "from", "inception"]):
                normalized = _norm_date(content)
                if normalized:
                    out["policy_start_date"] = normalized

            # Policy expiry date
            if not out["insurance_expiry"] and any(term in field_name_lower for term in ["expiry", "expiration", "expire", "end", "till", "until"]):
                normalized = _norm_date(content)
                if normalized:
                    out["insurance_expiry"] = normalized

    # Try key-value pairs as fallback
    if not all([out["policy_number"], out["insurance_provider"]]):
        kv_pairs = ar.get("keyValuePairs") or []
        for pair in kv_pairs:
            key_content = (pair.get("key") or {}).get("content", "").lower()
            value_content = (pair.get("value") or {}).get("content", "")

            if not value_content:
                continue

            # Policy number
            if not out["policy_number"] and any(term in key_content for term in ["policy", "certificate", "number"]):
                policy_match = re.search(r"[A-Z0-9]{5,}", value_content.replace(" ", ""))
                if policy_match:
                    out["policy_number"] = policy_match.group()

            # Insurance provider
            if not out["insurance_provider"] and any(term in key_content for term in ["insurer", "provider", "company"]):
                out["insurance_provider"] = value_content.strip()

            # Insured name
            if not out["insured_name"] and any(term in key_content for term in ["insured", "policyholder", "owner"]):
                out["insured_name"] = value_content.strip()

            # Premium
            if not out["premium_amount"] and any(term in key_content for term in ["premium", "amount", "cost"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", value_content.replace(",", ""))
                if amt:
                    out["premium_amount"] = float(amt.group().replace(",", ""))

            # Sum insured
            if not out["sum_insured"] and any(term in key_content for term in ["sum", "value", "insured"]):
                amt = re.search(r"[\d,]+(?:\.\d{2})?", value_content.replace(",", ""))
                if amt:
                    out["sum_insured"] = float(amt.group().replace(",", ""))

            # Dates
            if not out["policy_start_date"] and any(term in key_content for term in ["start", "effective", "from"]):
                out["policy_start_date"] = _norm_date(value_content)

            if not out["insurance_expiry"] and any(term in key_content for term in ["expiry", "expiration", "end"]):
                out["insurance_expiry"] = _norm_date(value_content)

    # Extract policy conditions from tables
    tables = ar.get("tables") or []
    for table in tables:
        cells = table.get("cells") or []

        # Try to identify coverage/conditions table
        for cell in cells:
            content = (cell.get("content") or "").lower()
            if any(term in content for term in ["coverage", "benefit", "condition", "insured", "limit"]):
                # This looks like a coverage table, parse it
                out["policy_conditions"] = _parse_coverage_table(table)
                break

        if out["policy_conditions"]:
            break

    return out


def _map_insurance_policy_text(text):
    """Fallback regex mapping for Insurance Policy from raw text"""
    out = {
        "policy_number": None,
        "insurance_provider": None,
        "insured_name": None,
        "policy_start_date": None,
        "insurance_expiry": None,
        "premium_amount": None,
        "coverage_type": None,
        "sum_insured": None,
        "policy_conditions": []
    }

    # Policy number - look for patterns
    policy_patterns = [
        r"(?:Policy|Certificate)\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9\-/]{5,25})",
        r"\b([A-Z]{2,5}\d{5,15})\b"  # Alphanumeric policy numbers
    ]
    for pattern in policy_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["policy_number"] = m.group(1).strip()
            break

    # Insurance provider - look for company names
    provider_patterns = [
        r"(?:Insurer|Insurance\s*Company|Provider|Underwriter)\s*[:\-]?\s*([A-Za-z\s&]{5,50})",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Insurance)",  # "ABC Insurance"
    ]
    for pattern in provider_patterns:
        m = re.search(pattern, text, re.I | re.M)
        if m:
            provider = m.group(1).strip()
            # Validate it's not a generic term
            if len(provider) > 5 and provider.lower() not in ["the insurance", "insurance company"]:
                out["insurance_provider"] = provider
                break

    # Insured name - look after "Insured" or "Policyholder"
    name_patterns = [
        r"(?:Insured\s*Name|Policyholder|Owner)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
    ]
    for pattern in name_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["insured_name"] = m.group(1).strip()
            break

    # Premium amount
    premium_patterns = [
        r"(?:Premium|Total\s*Premium|Annual\s*Premium)\s*[:\-]?\s*(?:AED|USD|SAR)?\s*([\d,]+(?:\.\d{2})?)",
    ]
    for pattern in premium_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["premium_amount"] = float(m.group(1).replace(",", ""))
            break

    # Sum insured / Vehicle value
    value_patterns = [
        r"(?:Sum\s*Insured|Vehicle\s*Value|Market\s*Value|Insured\s*Value)\s*[:\-]?\s*(?:AED|USD|SAR)?\s*([\d,]+(?:\.\d{2})?)",
    ]
    for pattern in value_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["sum_insured"] = float(m.group(1).replace(",", ""))
            break

    # Coverage type
    if re.search(r"\bComprehensive\b", text, re.I):
        out["coverage_type"] = "Comprehensive"
    elif re.search(r"Third\s*Party\s*Fire\s*(?:and|&)?\s*Theft", text, re.I):
        out["coverage_type"] = "Third Party Fire & Theft"
    elif re.search(r"Third\s*Party", text, re.I):
        out["coverage_type"] = "Third Party"

    # Dates
    DATE_RX = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"

    # Start date
    start_patterns = [
        r"(?:Policy\s*Start|Effective\s*Date|Effective\s*From|Inception)\s*[:\-]?\s*" + DATE_RX,
        r"(?:From)\s*[:\-]?\s*" + DATE_RX
    ]
    for pattern in start_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["policy_start_date"] = _norm_date(m.group(1))
            break

    # Expiry date
    expiry_patterns = [
        r"(?:Expiry|Expiration|Expire\s*Date|Policy\s*End|Valid\s*Until)\s*[:\-]?\s*" + DATE_RX,
    ]
    for pattern in expiry_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            out["insurance_expiry"] = _norm_date(m.group(1))
            break

    # Extract coverage items from text (simplified - look for common terms)
    coverage_keywords = [
        "Comprehensive Coverage", "Third Party Liability", "Collision",
        "Personal Accident", "Passenger Coverage", "Roadside Assistance",
        "Agency Repair", "Natural Disasters", "Theft", "Fire",
        "GCC Coverage", "Replacement Vehicle"
    ]

    for keyword in coverage_keywords:
        if re.search(r"\b" + re.escape(keyword) + r"\b", text, re.I):
            out["policy_conditions"].append({
                "coverage_item": keyword,
                "description": f"Covered as per policy terms"
            })

    return out


def _parse_coverage_table(table):
    """Parse a table structure to extract policy conditions/coverage items"""
    conditions = []
    cells = table.get("cells") or []

    # Group cells by row
    rows = {}
    for cell in cells:
        row_index = cell.get("rowIndex", 0)
        if row_index not in rows:
            rows[row_index] = []
        rows[row_index].append(cell)

    # Skip header row (row 0), process data rows
    for row_index in sorted(rows.keys()):
        if row_index == 0:  # Skip header
            continue

        row_cells = sorted(rows[row_index], key=lambda c: c.get("columnIndex", 0))

        if len(row_cells) >= 2:
            # Assume first column is coverage item, rest are details
            coverage_item = row_cells[0].get("content", "").strip()
            description = " ".join([c.get("content", "") for c in row_cells[1:]]).strip()

            # Try to extract amount from description
            coverage_amount = None
            deductible = None

            amt_match = re.search(r"(?:AED|USD|SAR)?\s*([\d,]+(?:\.\d{2})?)", description)
            if amt_match:
                coverage_amount = float(amt_match.group(1).replace(",", ""))

            ded_match = re.search(r"(?:Deductible|Excess)[:\-]?\s*(?:AED|USD|SAR)?\s*([\d,]+(?:\.\d{2})?)", description, re.I)
            if ded_match:
                deductible = float(ded_match.group(1).replace(",", ""))

            if coverage_item and len(coverage_item) > 2:
                condition = {
                    "coverage_item": coverage_item if len(coverage_item) < 100 else "Other",
                    "description": description[:500],  # Limit description length
                }
                if coverage_amount:
                    condition["coverage_amount"] = coverage_amount
                if deductible:
                    condition["deductible"] = deductible

                conditions.append(condition)

    return conditions
