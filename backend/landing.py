"""
landing.py – HTML Landing Page Generator für Angebote
Spiegelt die PDF-Struktur: Cover, Übersicht, Detailseiten, Preise, Leasing, Dokumente, Bestellen
"""
import html as _html


def _e(v) -> str:
    return _html.escape(str(v or ''))


def _money(n) -> str:
    try:
        n = float(n or 0)
    except (ValueError, TypeError):
        n = 0.0
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _nl2br(text: str) -> str:
    return _e(text).replace("\n", "<br>")


def _img_src(url: str, backend_base: str = "") -> str:
    if not url:
        return ""
    if url.startswith("/uploads/"):
        return backend_base + url
    return url


def _calc_leasing(kaufpreis: float, settings: dict) -> list:
    durations = [36, 48, 60]
    raw_factors = settings.get("leasing_factors") or {}
    fee = float(settings.get("leasing_processing_fee") or 100)
    vat = float(settings.get("leasing_vat") or 20) / 100
    breaks = [10000, 20000, 30000, 50000, 999999]
    brk = str(next((b for b in breaks if kaufpreis <= b), 999999))
    result = []
    for dur in durations:
        f = raw_factors.get(str(dur)) or raw_factors.get(dur) or {}
        factor = float(f.get(brk) or f.get(str(brk)) or 0)
        if factor == 0:
            continue
        monthly = round(kaufpreis * factor / 100 * 100) / 100
        legal = round((36 * monthly * (1 + vat) + fee * (1 + vat)) * 0.01 * 100) / 100
        result.append({"dur": dur, "monthly": monthly, "fee": fee, "legal": legal})
    return result


def generate_html(offer: dict, settings: dict) -> str:
    import os
    backend_base = os.environ.get("BACKEND_BASE_URL", "").rstrip("/")

    project = offer.get("project") or {}
    items = offer.get("offer_items") or []
    leasing_data = offer.get("leasing") or {}

    offer_no     = project.get("offerNo") or offer.get("offer_no") or ""
    customer     = project.get("customer") or ""
    contact_name = project.get("contact") or ""
    cust_pos     = project.get("customer_position") or ""
    customer_email = project.get("customerEmail") or ""
    customer_phone = project.get("customer_phone") or ""
    customer_mobile = project.get("customer_mobile") or ""
    project_name = project.get("project") or ""
    valid_date   = project.get("valid") or ""
    date_created = project.get("date") or ""
    street       = project.get("customer_street") or ""
    zip_code     = project.get("customer_zip") or ""
    city         = project.get("customer_city") or ""
    delivery     = project.get("delivery_address") or ""
    payment_term = project.get("payment_term") or ""
    vat_country  = project.get("vat_country") or ""
    vat_rate     = project.get("vat_rate")
    cust_logo_url = project.get("customer_logo") or ""
    version      = project.get("version") or "1.0"

    zip_url      = offer.get("zip_url") or ""
    zip_filename = offer.get("zip_filename") or "Angebot.zip"

    provider_name    = settings.get("company") or "Sielaff Austria GmbH"
    provider_email   = settings.get("email") or "info@at.sielaff.com"
    provider_phone   = settings.get("phone") or ""
    provider_address = settings.get("address") or ""
    provider_website = settings.get("website") or ""
    provider_contact = settings.get("contact_person") or ""
    logo_url         = settings.get("logo_image") or ""
    cover_url        = settings.get("cover_image") or ""
    legal_notice     = settings.get("legal_notice") or ""

    # Totals
    one_time = sum(float(i.get("price") or 0) for i in items if not i.get("recurring") and not i.get("optional"))
    monthly  = sum(float(i.get("price") or 0) for i in items if i.get("recurring") and not i.get("optional"))
    discount_pct   = float(project.get("discount_percent") or 0)
    original_total = sum(float(i.get("original_price") or i.get("price") or 0) for i in items if not i.get("recurring") and not i.get("optional"))
    saved = original_total - one_time

    # Documents
    seen_docs: set = set()
    docs: list = []
    for item in items:
        for doc in (item.get("documents") or []):
            title = (doc.get("title") or "").strip()
            url = doc.get("file_url") or ""
            if title and title not in seen_docs and url:
                seen_docs.add(title)
                docs.append({"title": title, "url": url})

    # Leasing
    leasing_enabled = leasing_data.get("enabled", False)
    leasing_rows = []
    if leasing_enabled and one_time > 0:
        leasing_rows = _calc_leasing(one_time, settings)

    # mailto
    mailto_subject = f"Auftragserteilung Angebot {offer_no}"
    mailto_body = (
        f"Sehr geehrte Damen und Herren,%0A%0A"
        f"hiermit beauftragen wir Sie verbindlich gem%C3%A4%C3%9F Angebot {offer_no}.%0A%0A"
        f"Mit freundlichen Gr%C3%BC%C3%9Fen%0A{_e(customer)}"
    )
    mailto_href = f"mailto:{provider_email}?subject={mailto_subject}&body={mailto_body}"

    # ── Logo HTML ──────────────────────────────────────────────────────────────
    logo_src = _img_src(logo_url, backend_base)
    logo_html = (
        f'<img src="{_e(logo_src)}" alt="{_e(provider_name)}" class="header-logo">'
        if logo_src else
        f'<div class="logo-fallback">S</div>'
    )

    # ── Cover-Foto ─────────────────────────────────────────────────────────────
    cover_src = _img_src(cover_url, backend_base)
    cover_style = (
        f'background-image:url("{_e(cover_src)}");background-size:cover;background-position:center;'
        if cover_src else ""
    )

    # ── Nav-Tabs (zeigen/verstecken per JS) ────────────────────────────────────
    nav_items = '<a href="#" onclick="showTab(\'uebersicht\');return false" data-tab="uebersicht" class="nav-active">Übersicht</a>'
    if leasing_rows:
        nav_items += '<a href="#" onclick="showTab(\'leasing\');return false" data-tab="leasing">Leasing</a>'
    nav_items += '<a href="#" onclick="showTab(\'preise\');return false" data-tab="preise">Preiszusammenfassung</a>'
    nav_items += '<a href="#" onclick="showTab(\'details\');return false" data-tab="details">Detailbeschreibungen</a>'
    for di, doc in enumerate(docs):
        short_label = doc["title"] if len(doc["title"]) <= 22 else doc["title"][:20] + "…"
        nav_items += f'<a href="#" onclick="showTab(\'doc-{di}\');return false" data-tab="doc-{di}">&#128196; {_e(short_label)}</a>'
    nav_items += '<a href="#" onclick="showTab(\'bestellen\');return false" data-tab="bestellen">Bestellen</a>'

    # ── Angebotsübersicht-Tabelle (wie PDF) ────────────────────────────────────
    overview_rows = ""
    for idx, item in enumerate(items, 1):
        name   = _e(item.get("name") or "")
        cluster = _e(item.get("cluster") or "")
        price  = float(item.get("price") or 0)
        orig   = float(item.get("original_price") or price)
        disc   = float(item.get("discount_pct") or 0)
        is_opt = bool(item.get("optional"))
        is_rec = bool(item.get("recurring"))
        qty    = int(item.get("qty") or 1)

        if is_opt:
            suffix = "/Mo." if is_rec else ""
            price_cell = f'<span class="muted">optional ({_money(orig)}{suffix})</span>'
        elif disc > 0:
            suffix = "/Mo." if is_rec else ""
            price_cell = (f'<span class="strike muted">{_money(orig * qty)}{suffix}</span> '
                          f'<strong class="red">{_money(price * qty)}{suffix}</strong>')
        elif orig == 0 and not is_opt:
            price_cell = '<span class="muted">inklusive</span>'
        else:
            suffix = "/Mo." if is_rec else ""
            price_cell = f'<strong>{_money(price * qty)}{suffix}</strong>'

        badges = ""
        if is_opt:
            badges += '<span class="badge badge-opt">Optional</span>'
        if disc > 0:
            d_int = int(disc) if disc == int(disc) else disc
            badges += f'<span class="badge badge-disc">–{d_int}%</span>'

        overview_rows += f"""
        <tr>
          <td class="pos-num">{idx}</td>
          <td><span class="item-name">{name}</span>{(' ' + badges) if badges else ''}</td>
          <td class="muted small">{cluster}</td>
          <td class="text-right">{price_cell}</td>
        </tr>"""

    # Summenzeilen
    if saved > 0.005:
        d_int = int(discount_pct) if discount_pct == int(discount_pct) else discount_pct
        overview_rows += f"""
        <tr class="sum-sep">
          <td colspan="2"></td>
          <td class="muted small text-right">Zwischensumme</td>
          <td class="text-right muted">{_money(original_total)}</td>
        </tr>
        <tr>
          <td colspan="2"></td>
          <td class="small text-right green">Rabatt {d_int}%</td>
          <td class="text-right green">− {_money(saved)}</td>
        </tr>"""
    overview_rows += f"""
        <tr class="total-row">
          <td colspan="2"></td>
          <td class="text-right">Gesamt netto</td>
          <td class="text-right red"><strong>{_money(one_time)}</strong></td>
        </tr>"""
    if monthly > 0:
        overview_rows += f"""
        <tr class="total-row">
          <td colspan="2"></td>
          <td class="text-right">Monatlich</td>
          <td class="text-right"><strong>{_money(monthly)}/Mo.</strong></td>
        </tr>"""

    # ── Detailbeschreibungen (mit Produktbild, Kurz-/Langtext) ─────────────────
    detail_blocks = ""
    for idx, item in enumerate(items, 1):
        name    = _e(item.get("name") or "")
        short_t = item.get("short_text") or ""
        long_t  = item.get("long_text") or ""
        price   = float(item.get("price") or 0)
        orig    = float(item.get("original_price") or price)
        disc    = float(item.get("discount_pct") or 0)
        is_opt  = bool(item.get("optional"))
        is_rec  = bool(item.get("recurring"))
        qty     = int(item.get("qty") or 1)
        cluster = _e(item.get("cluster") or "")
        display = (item.get("display_type") or "Großes Bild + Beschreibung").strip()
        img_url = _img_src(item.get("image_path") or "", backend_base)

        # Preis-String
        if is_opt:
            suffix = "/Mo." if is_rec else ""
            ps = f'Optional ({_money(orig)}{suffix})'
        elif disc > 0:
            d_int = int(disc) if disc == int(disc) else disc
            suffix = "/Mo." if is_rec else ""
            ps = f'{_money(price * qty)}{suffix} <span class="badge badge-disc">–{d_int}%</span>'
        elif orig == 0:
            ps = "Inklusive"
        else:
            suffix = "/Mo." if is_rec else ""
            ps = f'{_money(price * qty)}{suffix}'

        # Bild-HTML je Display-Typ
        img_html = ""
        if img_url and display != "Kein Bild, Langtext + Kurztext" and display != "Kein Bild, Kurztext":
            if display == "Kleines Bild + Langtext":
                img_html = f'<img src="{_e(img_url)}" class="detail-img detail-img-sm" alt="{name}" loading="lazy">'
            else:
                img_html = f'<img src="{_e(img_url)}" class="detail-img" alt="{name}" loading="lazy">'

        # Layout: kleines Bild links + text rechts
        if img_url and display == "Kleines Bild + Langtext":
            text_part = ""
            if short_t:
                text_part += f'<p class="detail-short">{_nl2br(short_t)}</p>'
            if long_t:
                text_part += f'<div class="detail-long">{_nl2br(long_t)}</div>'
            content_html = f"""
              <div class="detail-row">
                {img_html}
                <div class="detail-text">{text_part}</div>
              </div>"""
        else:
            content_html = img_html
            if short_t:
                content_html += f'<p class="detail-short">{_nl2br(short_t)}</p>'
            if long_t:
                content_html += f'<div class="detail-long">{_nl2br(long_t)}</div>'

        badges = ""
        if is_opt:
            badges += '<span class="badge badge-opt">Optional</span>'
        if disc > 0:
            d_int = int(disc) if disc == int(disc) else disc
            badges += f'<span class="badge badge-disc">–{d_int}%</span>'

        detail_blocks += f"""
      <div class="detail-block" id="pos-{idx}">
        <div class="detail-header">
          <div>
            <div class="detail-num">Position {idx}{f' &middot; {cluster}' if cluster else ''}</div>
            <div class="detail-name">{name} {badges}</div>
          </div>
          <div class="detail-price {'detail-price-opt' if is_opt else ''}">{ps}</div>
        </div>
        <div class="detail-content">{content_html}</div>
      </div>"""

    # ── Leasing-Sektion ────────────────────────────────────────────────────────
    leasing_section = ""
    if leasing_rows:
        cards = ""
        for i, row in enumerate(leasing_rows):
            hi = " lc-hi" if i == 1 else ""
            badge = '<div class="lc-badge">Empfohlen</div>' if i == 1 else ""
            cards += f"""
            <div class="lc{hi}">
              <div class="lc-mo">{row['dur']} Monate</div>
              <div class="lc-rate">{_money(row['monthly'])}</div>
              <div class="lc-sub">pro Monat, netto</div>
              {badge}
            </div>"""
        leasing_section = f"""
      <div class="sec tab-section" data-tab="leasing">
        <div class="sec-label">2 · Leasing-Finanzierung</div>
        <div class="sec-title">Ihre Finanzierungsoptionen</div>
        <p class="muted small" style="margin-bottom:16px">Finanzierungsbetrag {_money(one_time)} &middot; vorbehaltlich Bonitätsprüfung</p>
        <div class="lc-grid">{cards}</div>
        <p class="fn">Alle Raten zzgl. MwSt. Angaben unverbindlich. Leasingrate = Kaufpreis × Faktor / 100.</p>
      </div>"""

    # ── Dokumente: je ein Tab pro Dokument + ZIP-Block ────────────────────────
    docs_section = ""
    if docs:
        for di, doc in enumerate(docs):
            n_label = f"{di + 1} / {len(docs)}"
            docs_section += f"""
      <div class="sec tab-section" data-tab="doc-{di}">
        <div class="doc-tab-header">
          <div>
            <div class="sec-label">Anhang {n_label}</div>
            <div class="sec-title" style="margin-bottom:10px">{_e(doc['title'])}</div>
          </div>
          <a href="{_e(doc['url'])}" target="_blank" rel="noopener" class="doc-dl-btn">&#8659; Herunterladen</a>
        </div>
        <div class="pdf-frame">
          <iframe src="{_e(doc['url'])}" title="{_e(doc['title'])}" loading="lazy"></iframe>
        </div>
      </div>"""
        # ZIP-Download als eigene Sektion, die bei jedem Doc-Tab mit angezeigt wird
        if zip_url:
            docs_section += f"""
      <div class="zip-bar tab-section" data-tab="{'|'.join(f'doc-{i}' for i in range(len(docs)))}">
        <div class="zip-icon">&#128230;</div>
        <div class="zip-text">
          <div class="zip-title">Alle Anhänge als ZIP herunterladen</div>
          <div class="zip-sub">{_e(zip_filename)}</div>
        </div>
        <a href="{_e(zip_url)}" class="zip-btn" download>&#8659; ZIP laden</a>
      </div>"""

    # ── Kundenadresse ──────────────────────────────────────────────────────────
    cust_logo_src = _img_src(cust_logo_url, backend_base)
    cust_logo_html = f'<img src="{_e(cust_logo_src)}" alt="{_e(customer)}" class="cust-logo">' if cust_logo_src else ""
    addr_parts = [p for p in [street, f"{zip_code} {city}".strip()] if p.strip()]
    addr_str   = ", ".join(addr_parts)

    kd_rows = f'<div class="kd-item"><span class="kd-lbl">Firma</span><span class="kd-val"><strong>{_e(customer)}</strong></span></div>'
    if contact_name:
        contact_line = _e(contact_name) + (f', {_e(cust_pos)}' if cust_pos else '')
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">Ansprechpartner</span><span class="kd-val">{contact_line}</span></div>'
    if customer_email:
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">E-Mail</span><span class="kd-val"><a href="mailto:{_e(customer_email)}">{_e(customer_email)}</a></span></div>'
    tel_parts = []
    if customer_phone:  tel_parts.append(f'Tel: {_e(customer_phone)}')
    if customer_mobile: tel_parts.append(f'Mobil: {_e(customer_mobile)}')
    if tel_parts:
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">Telefon</span><span class="kd-val">{" &middot; ".join(tel_parts)}</span></div>'
    if project_name:
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">Projekt</span><span class="kd-val">{_e(project_name)}</span></div>'
    if addr_str:
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">Adresse</span><span class="kd-val">{_e(addr_str)}</span></div>'
    if delivery:
        kd_rows += f'<div class="kd-item"><span class="kd-lbl">Lieferadresse</span><span class="kd-val">{_e(delivery)}</span></div>'

    # ── Preisinformationen (Preiszusammenfassung) ──────────────────────────────
    price_rows = ""
    if saved > 0.005:
        d_int = int(discount_pct) if discount_pct == int(discount_pct) else discount_pct
        price_rows += f"""
          <div class="pr-row"><span>Zwischensumme</span><span class="muted">{_money(original_total)}</span></div>
          <div class="pr-row green"><span>Rabatt {d_int}%</span><span>− {_money(saved)}</span></div>"""
    price_rows += f"""
          <div class="pr-row pr-total"><span>Einmalig netto</span><span class="red"><strong>{_money(one_time)}</strong></span></div>"""
    if monthly > 0:
        price_rows += f"""
          <div class="pr-row"><span>Monatlich (Servicevertrag)</span><span><strong>{_money(monthly)}/Mo.</strong></span></div>"""
    if vat_country and vat_rate is not None:
        price_rows += f"""
          <div class="pr-row muted small"><span>zzgl. {vat_rate:g}% MwSt ({_e(vat_country)})</span><span></span></div>"""
    if payment_term:
        price_rows += f"""
          <div class="pr-row muted small"><span>Zahlungsziel: {_e(payment_term)}</span><span></span></div>"""

    # ── Provider-Kontakt im Bestellblock ──────────────────────────────────────
    prov_contact_rows = ""
    if provider_contact:
        prov_contact_rows += f'<div class="cr">&#128100; {_e(provider_contact)}</div>'
    if provider_phone:
        prov_contact_rows += f'<div class="cr">&#128222; <a href="tel:{_e(provider_phone)}" style="color:rgba(255,255,255,.8)">{_e(provider_phone)}</a></div>'
    if provider_email:
        prov_contact_rows += f'<div class="cr">&#9993; <a href="mailto:{_e(provider_email)}" style="color:rgba(255,255,255,.8)">{_e(provider_email)}</a></div>'
    if provider_website:
        prov_contact_rows += f'<div class="cr">&#127760; {_e(provider_website)}</div>'

    # ── AGB / Rechtliche Hinweise ──────────────────────────────────────────────
    if not legal_notice:
        legal_notice = (
            "Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen "
            "Mehrwertsteuer. Es gelten die allgemeinen Geschäftsbedingungen der "
            f"{provider_name} in der jeweils gültigen Fassung."
        )
    legal_paras = "".join(
        f'<p style="margin-bottom:8px">{_e(p.strip())}</p>'
        for p in legal_notice.split("\n") if p.strip()
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Angebot {_e(offer_no)} – {_e(customer)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:#f4f4f5;color:#1a1a1a;line-height:1.6;padding-top:130px}}
a{{color:#c1121f;text-decoration:none}}a:hover{{text-decoration:underline}}

/* ── Header (Zeile 1) ────────────── */
.site-header{{background:#fff;border-bottom:1px solid #e4e4e7;padding:0 16px;display:flex;align-items:center;justify-content:space-between;height:42px;position:fixed;top:0;left:0;right:0;z-index:102;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.header-logo{{height:24px;max-width:80px;object-fit:contain}}
.logo-fallback{{width:24px;height:24px;background:#c1121f;border-radius:5px;color:#fff;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center}}
.header-offer{{font-size:13px;font-weight:700;color:#1a1a1a;letter-spacing:-.2px}}
.header-meta{{font-size:11px;color:#888}}

/* ── Info-Bar (Zeile 2) ──────────── */
.info-bar{{background:linear-gradient(90deg,#7a0010,#c1121f);position:fixed;top:42px;left:0;right:0;z-index:101;overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch}}
.info-bar-inner{{display:inline-flex;padding:0 16px;min-width:100%}}
.ib-cell{{display:inline-flex;flex-direction:column;justify-content:center;padding:8px 16px 8px 0;border-right:1px solid rgba(255,255,255,.15);margin-right:16px}}
.ib-cell:last-child{{border-right:none;margin-right:0}}
.ib-lbl{{font-size:9px;text-transform:uppercase;letter-spacing:.7px;color:rgba(255,255,255,.6);font-weight:700;margin-bottom:2px}}
.ib-val{{font-size:12px;font-weight:700;color:#fff;line-height:1.2}}
.ib-val.green{{color:#4ade80}}

/* ── Nav (Zeile 3) ───────────────── */
.sticky-nav{{background:#1d1d1d;position:fixed;top:88px;left:0;right:0;z-index:100;overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch}}
.sticky-nav a{{display:inline-block;padding:10px 16px;color:rgba(255,255,255,.65);font-size:12px;font-weight:600;text-decoration:none;border-bottom:2px solid transparent;letter-spacing:.2px;transition:color .15s,border-color .15s;cursor:pointer}}
.sticky-nav a:hover{{color:#fff;border-bottom-color:rgba(193,18,31,.6);text-decoration:none}}
.sticky-nav a.nav-active{{color:#fff;border-bottom-color:#c1121f}}
.tab-section{{display:none}}.tab-section.tab-visible{{display:block}}

/* ── Wrapper ─────────────────────── */
.wrap{{max-width:760px;margin:0 auto;padding:0 0 60px}}

/* ── Sektionen ───────────────────── */
.sec{{background:#fff;border:1px solid #e4e4e7;border-radius:14px;margin:16px 16px 0;padding:22px 24px;scroll-margin-top:138px}}
.sec-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#c1121f;margin-bottom:4px}}
.sec-title{{font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:16px}}
.muted{{color:#71717a}}
.small{{font-size:12px}}
.green{{color:#16a34a}}
.red{{color:#c1121f}}
.strike{{text-decoration:line-through}}
.text-right{{text-align:right}}

/* ── Kundendaten ─────────────────── */
.kd-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}}
.cust-logo{{max-height:50px;max-width:140px;object-fit:contain}}
.kd-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px}}
.kd-item{{display:flex;flex-direction:column;gap:1px}}
.kd-lbl{{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.kd-val{{font-size:14px;color:#1a1a1a}}
.kd-val a{{color:#c1121f}}

/* ── Übersichtstabelle ───────────── */
.overview-table{{width:100%;border-collapse:collapse;font-size:13px}}
.overview-table thead th{{background:#f4f4f5;padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #e4e4e7}}
.overview-table thead th:last-child{{text-align:right}}
.overview-table tbody tr{{border-bottom:1px solid #f0f0f0}}
.overview-table tbody tr:last-child{{border-bottom:none}}
.overview-table td{{padding:10px 10px;vertical-align:middle}}
.pos-num{{color:#aaa;font-size:11px;width:28px}}
.item-name{{font-weight:500}}
.badge{{display:inline-block;font-size:10px;padding:1px 6px;border-radius:12px;margin-left:4px;vertical-align:middle}}
.badge-opt{{background:#fef3c7;color:#92400e;border:1px solid #fde68a}}
.badge-disc{{background:#dcfce7;color:#166534;border:1px solid #bbf7d0}}
.sum-sep td{{border-top:1px solid #e4e4e7!important;padding-top:10px!important}}
.total-row td{{font-size:14px;border-top:2px solid #e4e4e7;padding-top:12px;padding-bottom:12px}}

/* ── Detail-Beschreibungen ───────── */
.detail-block{{border-bottom:1px solid #f0f0f0;padding:24px 0}}
.detail-block:first-child{{padding-top:0}}
.detail-block:last-child{{border-bottom:none;padding-bottom:0}}
.detail-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:12px}}
.detail-num{{font-size:11px;color:#888;margin-bottom:2px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.detail-name{{font-size:17px;font-weight:700;color:#1a1a1a;line-height:1.3}}
.detail-price{{font-size:15px;font-weight:600;color:#c1121f;text-align:right;flex-shrink:0;white-space:nowrap}}
.detail-price-opt{{color:#888;font-weight:400}}
.detail-img{{width:100%;max-height:340px;object-fit:contain;border-radius:8px;background:#f9f9f9;display:block;margin-bottom:14px}}
.detail-img-sm{{width:180px;max-height:160px;object-fit:contain;border-radius:8px;background:#f9f9f9;flex-shrink:0}}
.detail-row{{display:flex;gap:16px;align-items:flex-start}}
.detail-text{{flex:1}}
.detail-short{{font-size:14px;font-weight:600;color:#1a1a1a;margin-bottom:8px;line-height:1.5}}
.detail-long{{font-size:13px;color:#444;line-height:1.75}}
.detail-content{{font-size:13px;color:#444;line-height:1.75}}

/* ── Preiszusammenfassung ────────── */
.price-boxes{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}}
.price-box{{background:#f9f9f9;border:1px solid #e4e4e7;border-radius:10px;padding:16px}}
.price-box-lbl{{font-size:11px;color:#888;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.price-box-val{{font-size:26px;font-weight:700}}
.price-box-val.red{{color:#c1121f}}
.price-box-sub{{font-size:11px;color:#888;margin-top:3px}}
.pr-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:13px}}
.pr-row:last-child{{border-bottom:none}}
.pr-total{{font-size:15px;border-top:2px solid #e4e4e7;padding-top:10px;margin-top:4px}}

/* ── Leasing ─────────────────────── */
.lc-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:10px}}
.lc{{background:#f9f9f9;border:1px solid #e4e4e7;border-radius:10px;padding:16px;text-align:center}}
.lc-hi{{border-color:#c1121f;background:#fff5f5;position:relative}}
.lc-mo{{font-size:11px;color:#888;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.lc-rate{{font-size:22px;font-weight:700;color:#1a1a1a}}
.lc-sub{{font-size:11px;color:#888;margin-top:3px}}
.lc-badge{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:12px;margin-top:8px;background:rgba(193,18,31,.12);color:#a50f18;font-weight:600}}
.fn{{font-size:11px;color:#888;line-height:1.6;margin-top:6px}}

/* ── Dokumente ───────────────────── */
.doc-tab-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px}}
.doc-dl-btn{{display:inline-block;font-size:13px;font-weight:600;color:#c1121f;white-space:nowrap;border:1.5px solid #c1121f;border-radius:8px;padding:8px 14px;flex-shrink:0;text-decoration:none}}
.doc-dl-btn:hover{{background:#fff0f0;text-decoration:none}}
.pdf-frame{{border:1px solid #e4e4e7;border-radius:10px;overflow:hidden;height:520px}}
.pdf-frame iframe{{width:100%;height:100%;border:none;display:block}}
/* ── ZIP-Bar ─────────────────────── */
.zip-bar{{display:flex;align-items:center;gap:14px;background:#fff;border:1.5px solid #e4e4e7;border-radius:14px;margin:16px 16px 0;padding:16px 20px}}
.zip-bar.tab-visible{{display:flex}}
.zip-icon{{font-size:28px;flex-shrink:0}}
.zip-text{{flex:1}}
.zip-title{{font-size:14px;font-weight:600;color:#1a1a1a}}
.zip-sub{{font-size:11px;color:#888;margin-top:2px}}
.zip-btn{{display:inline-block;background:#c1121f;color:#fff;font-size:13px;font-weight:700;padding:10px 18px;border-radius:9px;white-space:nowrap;text-decoration:none}}
.zip-btn:hover{{background:#a50f18;text-decoration:none;color:#fff}}

/* ── Bestellen ───────────────────── */
.order-box{{background:linear-gradient(140deg,#7a0010 0%,#c1121f 60%,#e63946 100%);border-radius:14px;margin:16px 16px 0;padding:30px 24px;color:#fff;scroll-margin-top:138px}}
.order-label{{font-size:10px;text-transform:uppercase;letter-spacing:1px;opacity:.7;margin-bottom:6px}}
.order-title{{font-size:22px;font-weight:700;margin-bottom:8px}}
.order-sub{{font-size:14px;opacity:.85;margin-bottom:22px;line-height:1.65}}
.order-meta{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:22px}}
.om-box{{background:rgba(255,255,255,.12);border-radius:10px;padding:14px 16px;backdrop-filter:blur(4px)}}
.om-lbl{{font-size:10px;opacity:.7;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}}
.om-val{{font-size:16px;font-weight:700}}
.order-btn{{display:block;text-align:center;background:#fff;color:#c1121f;border-radius:10px;padding:15px;font-size:16px;font-weight:700;text-decoration:none;transition:background .15s}}
.order-btn:hover{{background:#fff5f5;text-decoration:none}}
.contact-strip{{margin-top:22px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2)}}
.cr{{font-size:13px;opacity:.85;margin-bottom:6px}}
.cr a{{color:rgba(255,255,255,.8)}}
.cr a:hover{{color:#fff;text-decoration:none}}

/* ── Legal ───────────────────────── */
.legal-sec{{background:#fff;border:1px solid #e4e4e7;border-radius:14px;margin:16px 16px 0;padding:20px 24px}}
.legal-sec .sec-label{{margin-bottom:10px}}
.legal-sec p{{font-size:11px;color:#888;line-height:1.7}}

/* ── Footer ──────────────────────── */
.footer{{text-align:center;padding:20px 16px 0;font-size:11px;color:#aaa;line-height:1.8}}

/* ── Responsive ──────────────────── */
@media(max-width:520px){{
  body{{padding-top:120px}}
  .sec{{margin:12px 10px 0;padding:16px}}
  .order-box{{margin:12px 10px 0;padding:20px 16px}}
  .legal-sec{{margin:12px 10px 0}}
  .kd-grid{{grid-template-columns:1fr}}
  .lc-grid{{grid-template-columns:1fr}}
  .price-boxes{{grid-template-columns:1fr}}
  .order-meta{{grid-template-columns:1fr}}
  .detail-row{{flex-direction:column}}
  .detail-img-sm{{width:100%;max-height:200px}}
  nav a{{font-size:12px;padding:10px 10px}}
}}
</style>
</head>
<body>

<!-- Zeile 1: Header ──────────────────────────────────────────────────────── -->
<header class="site-header">
  {logo_html}
  <div class="header-offer">{_e(offer_no)}</div>
  <div class="header-meta">{_e(provider_name)}</div>
</header>

<!-- Zeile 2: Info-Bar ────────────────────────────────────────────────────── -->
<div class="info-bar">
  <div class="info-bar-inner">
    {'<div class="ib-cell"><div class="ib-lbl">Angebotsnr.</div><div class="ib-val">' + _e(offer_no) + '</div></div>' if offer_no else ''}
    {'<div class="ib-cell"><div class="ib-lbl">Datum</div><div class="ib-val">' + _e(date_created) + '</div></div>' if date_created else ''}
    {'<div class="ib-cell"><div class="ib-lbl">Gültig bis</div><div class="ib-val green">' + _e(valid_date) + '</div></div>' if valid_date else ''}
    {'<div class="ib-cell"><div class="ib-lbl">Kunde</div><div class="ib-val">' + _e(customer) + '</div></div>' if customer else ''}
    {'<div class="ib-cell"><div class="ib-lbl">Ansprechpartner</div><div class="ib-val">' + _e(contact_name) + '</div></div>' if contact_name else ''}
    {'<div class="ib-cell"><div class="ib-lbl">Projekt</div><div class="ib-val">' + _e(project_name) + '</div></div>' if project_name else ''}
  </div>
</div>

<!-- Zeile 3: Navigation ──────────────────────────────────────────────────── -->
<div class="sticky-nav">{nav_items}</div>

<div class="wrap">

  <!-- ── 1. Angebotsübersicht ──────────────────────────────────────────── -->
  <div class="sec tab-section tab-visible" data-tab="uebersicht">
    <div class="sec-label">1 · Angebotsübersicht</div>
    <div class="sec-title">Positionen auf einen Blick</div>
    <table class="overview-table">
      <thead>
        <tr>
          <th style="width:30px">#</th>
          <th>Option / Leistung</th>
          <th style="width:120px">Cluster</th>
          <th style="width:140px;text-align:right">Preis</th>
        </tr>
      </thead>
      <tbody>{overview_rows}</tbody>
    </table>
  </div>

  <!-- ── 2. Leasing (optional) ──────────────────────────────────────────── -->
  {leasing_section}

  <!-- ── 3. Preiszusammenfassung ────────────────────────────────────────── -->
  <div class="sec tab-section" data-tab="preise">
    <div class="sec-label">{f'3' if leasing_rows else '2'} · Preiszusammenfassung</div>
    <div class="sec-title">Ihre Investition</div>
    <div class="kd-header" style="margin-bottom:16px">
      <div style="flex:1"><div class="kd-grid">{kd_rows}</div></div>
      {cust_logo_html}
    </div>
    <div class="price-boxes">
      <div class="price-box">
        <div class="price-box-lbl">Einmalig netto</div>
        <div class="price-box-val red">{_money(one_time)}</div>
        {f'<div class="price-box-sub">inkl. {int(discount_pct) if discount_pct == int(discount_pct) else discount_pct}% Rabatt</div>' if discount_pct > 0 else ''}
      </div>
      {f'<div class="price-box"><div class="price-box-lbl">Monatlich netto</div><div class="price-box-val">{_money(monthly)}</div><div class="price-box-sub">/ Monat, Servicevertrag</div></div>' if monthly > 0 else ''}
    </div>
    {price_rows}
  </div>

  <!-- ── 4. Detailbeschreibungen ────────────────────────────────────────── -->
  <div class="sec tab-section" data-tab="details">
    <div class="sec-label">{f'4' if leasing_rows else '3'} · Detailbeschreibungen</div>
    <div class="sec-title">Alle Leistungen im Detail</div>
    {detail_blocks}
  </div>

  <!-- ── 5. Anhänge ─────────────────────────────────────────────────────── -->
  {docs_section}

  <!-- ── Bestellen ──────────────────────────────────────────────────────── -->
  <div class="order-box tab-section" data-tab="bestellen">
    <div class="order-label">Angebot annehmen</div>
    <div class="order-title">Jetzt verbindlich bestellen</div>
    <div class="order-sub">
      Mit einem Klick beauftragen Sie uns rechtsverbindlich gemäß diesem Angebot.
      Sie erhalten umgehend eine Auftragsbestätigung per E-Mail.
      {f'<br><br>&#9200; Gültig bis <strong>{_e(valid_date)}</strong>' if valid_date else ''}
    </div>
    <div class="order-meta">
      <div class="om-box">
        <div class="om-lbl">Gesamtsumme netto</div>
        <div class="om-val">{_money(one_time)}</div>
      </div>
      <div class="om-box">
        <div class="om-lbl">Angebotsnummer</div>
        <div class="om-val">{_e(offer_no)}</div>
      </div>
    </div>
    <a href="{mailto_href}" class="order-btn">&#10003;&ensp;Jetzt verbindlich bestellen</a>
    <div class="contact-strip">
      {prov_contact_rows}
    </div>
  </div>

  <!-- ── Rechtliche Hinweise (immer sichtbar unter Bestellen) ──────────── -->
  <div class="legal-sec tab-section" data-tab="bestellen">
    <div class="sec-label">Rechtliche Hinweise</div>
    {legal_paras}
  </div>

  <div class="footer">
    {_e(provider_name)} &middot; Dieses Angebot wurde individuell für <strong>{_e(customer)}</strong> erstellt &middot; {_e(offer_no)}
    {f'<br>{_e(provider_address)}' if provider_address else ''}
  </div>

</div>
<script>
function showTab(id) {{
  document.querySelectorAll('.tab-section').forEach(function(el) {{
    var tabs = (el.dataset.tab || '').split('|');
    el.classList.toggle('tab-visible', tabs.indexOf(id) !== -1);
  }});
  document.querySelectorAll('.sticky-nav a').forEach(function(a) {{
    a.classList.toggle('nav-active', a.dataset.tab === id);
  }});
  window.scrollTo({{top: 0, behavior: 'smooth'}});
}}
</script>
</body>
</html>"""
