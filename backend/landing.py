"""
landing.py – HTML Landing Page Generator für Angebote
"""
import html as _html


def _e(v) -> str:
    """HTML-escape a value."""
    return _html.escape(str(v or ''))


def _money(n) -> str:
    try:
        n = float(n or 0)
    except (ValueError, TypeError):
        n = 0.0
    formatted = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def _nl2br(text: str) -> str:
    return _e(text).replace("\n", "<br>")


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
    project = offer.get("project") or {}
    items = offer.get("offer_items") or []
    leasing_data = offer.get("leasing") or {}

    offer_no = project.get("offerNo") or offer.get("offer_no") or ""
    customer = project.get("customer") or ""
    contact_name = project.get("contact") or ""
    customer_email = project.get("customerEmail") or ""
    project_name = project.get("project") or ""
    valid_date = project.get("valid") or ""
    date_created = project.get("date") or ""
    street = project.get("customer_street") or ""
    zip_code = project.get("customer_zip") or ""
    city = project.get("customer_city") or ""
    delivery = project.get("delivery_address") or ""

    provider_name = settings.get("company") or "Sielaff Austria GmbH"
    provider_email = settings.get("email") or "info@at.sielaff.com"
    provider_phone = settings.get("phone") or "0676/6570301"
    provider_contact = settings.get("contact_person") or ""

    # Totals
    one_time = sum(
        float(i.get("price") or 0)
        for i in items if not i.get("recurring") and not i.get("optional")
    )
    monthly = sum(
        float(i.get("price") or 0)
        for i in items if i.get("recurring") and not i.get("optional")
    )

    # Collect unique documents across all items
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

    # Discount info
    discount_pct = float(project.get("discount_percent") or 0)
    original_total = sum(
        float(i.get("original_price") or i.get("price") or 0)
        for i in items if not i.get("recurring") and not i.get("optional")
    )

    # mailto for order button
    mailto_subject = f"Auftragserteilung Angebot {_e(offer_no)}"
    mailto_body = (
        f"Sehr geehrte Damen und Herren,%0A%0A"
        f"hiermit beauftragen wir Sie verbindlich gem%C3%A4%C3%9F Angebot {offer_no}.%0A%0A"
        f"Mit freundlichen Gr%C3%BC%C3%9Fen%0A"
        f"{_e(customer)}"
    )
    mailto_href = f"mailto:{provider_email}?subject={mailto_subject}&body={mailto_body}"

    # ── Position rows ──────────────────────────────────────────────
    pos_html = ""
    for idx, item in enumerate(items, 1):
        name = _e(item.get("name") or "")
        long_text = _nl2br(item.get("long_text") or item.get("short_text") or "")
        price = float(item.get("price") or 0)
        orig = float(item.get("original_price") or price)
        qty = int(item.get("qty") or 1)
        is_recurring = bool(item.get("recurring"))
        is_optional = bool(item.get("optional"))
        disc = float(item.get("discount_pct") or 0)
        cluster = _e(item.get("cluster") or "")

        price_label = "inklusive" if price == 0 and not is_optional else (
            _money(price) + (" / Mo." if is_recurring else "")
        )
        total_price = price * qty if not is_recurring else price
        total_label = _money(total_price) + (" / Mo." if is_recurring else "")

        discount_badge = ""
        if disc > 0:
            discount_badge = f'<span class="tag tag-disc">– {int(disc) if disc == int(disc) else disc} %</span>'
        optional_badge = '<span class="tag tag-opt">Optional</span>' if is_optional else ""

        pos_html += f"""
        <div class="pos-item">
          <div class="pos-head">
            <div>
              <div class="pos-name">{name}</div>
              <div class="pos-sub">Pos. {idx}{f' &middot; {cluster}' if cluster else ''}{f' &middot; Menge: {qty}' if qty > 1 else ''}</div>
              <div class="pos-tags">{optional_badge}{discount_badge}</div>
            </div>
            <div class="pos-prices">
              <div class="pos-price{' pos-optional' if is_optional else ''}">{total_label}</div>
              {f'<div class="pos-orig">{_money(orig * qty)}</div>' if disc > 0 else ''}
            </div>
          </div>
          {f'<p class="pos-desc">{long_text}</p>' if long_text else ""}
        </div>"""

    # ── Summary rows ───────────────────────────────────────────────
    sum_rows = ""
    if discount_pct > 0 and original_total > one_time:
        sum_rows += f"""
        <div class="sum-row"><span class="sum-lbl">Zwischensumme</span><span>{_money(original_total)}</span></div>
        <div class="sum-row green"><span class="sum-lbl">Rabatt {int(discount_pct) if discount_pct == int(discount_pct) else discount_pct} %</span><span>− {_money(original_total - one_time)}</span></div>"""
    sum_rows += f"""
        <div class="sum-row total"><span class="sum-lbl">Gesamt netto</span><span>{_money(one_time)}</span></div>"""
    if monthly > 0:
        sum_rows += f"""
        <div class="sum-row"><span class="sum-lbl">Monatlich (Servicevertrag)</span><span>{_money(monthly)} / Mo.</span></div>"""

    # ── Leasing section ───────────────────────────────────────────
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
      <div class="sec" id="leasing">
        <div class="sec-title">&#128176; Leasing-Optionen</div>
        <p class="sec-sub">Finanzierungsbetrag {_money(one_time)} &middot; über unseren Leasingpartner, vorbehaltlich Bonitätsprüfung</p>
        <div class="lc-grid">{cards}</div>
        <p class="fn">Alle Raten zzgl. MwSt. Angaben unverbindlich.</p>
      </div>"""

    # ── Documents section ─────────────────────────────────────────
    docs_section = ""
    if docs:
        doc_items = ""
        for doc in docs:
            doc_items += f"""
          <div class="doc-item">
            <div class="doc-icon">&#128196;</div>
            <div class="doc-info">
              <div class="doc-name">{_e(doc['title'])}</div>
            </div>
            <a href="{_e(doc['url'])}" target="_blank" rel="noopener" class="doc-dl">Download</a>
          </div>
          <div class="pdf-frame">
            <iframe src="{_e(doc['url'])}" title="{_e(doc['title'])}"></iframe>
          </div>"""
        docs_section = f"""
      <div class="sec" id="dokumente">
        <div class="sec-title">&#128206; Dokumente &amp; Anhänge</div>
        {doc_items}
      </div>"""

    # ── Addresses ─────────────────────────────────────────────────
    addr_parts = [p for p in [street, f"{zip_code} {city}".strip()] if p.strip()]
    addr_str = ", ".join(addr_parts)
    billing_row = f'<div class="kd-item"><div class="kd-lbl">Adresse</div><div class="kd-val">{_e(addr_str)}</div></div>' if addr_str else ""
    delivery_row = f'<div class="kd-item"><div class="kd-lbl">Lieferadresse</div><div class="kd-val">{_e(delivery)}</div></div>' if delivery else ""
    email_row = f'<div class="kd-item"><div class="kd-lbl">E-Mail</div><div class="kd-val"><a href="mailto:{_e(customer_email)}">{_e(customer_email)}</a></div></div>' if customer_email else ""
    project_row = f'<div class="kd-item"><div class="kd-lbl">Projekt</div><div class="kd-val">{_e(project_name)}</div></div>' if project_name else ""

    # ── Nav: only show sections that have content ──────────────────
    nav_links = '<a href="#positionen">Positionen</a>'
    if leasing_rows:
        nav_links += '<a href="#leasing">Leasing</a>'
    if docs:
        nav_links += '<a href="#dokumente">Dokumente</a>'
    nav_links += '<a href="#bestellen">Bestellen</a>'

    # ── Provider contact block ─────────────────────────────────────
    provider_contact_html = ""
    if provider_contact:
        provider_contact_html = f'<div class="cr">&#128100; {_e(provider_contact)}</div>'
    if provider_phone:
        provider_contact_html += f'<div class="cr">&#128222; {_e(provider_phone)}</div>'
    if provider_email:
        provider_contact_html += f'<div class="cr">&#9993; <a href="mailto:{_e(provider_email)}" style="color:rgba(255,255,255,.8)">{_e(provider_email)}</a></div>'

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Angebot {_e(offer_no)} – {_e(customer)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:#f5f5f5;color:#1a1a1a;line-height:1.5}}
a{{color:#c1121f;text-decoration:none}}
a:hover{{text-decoration:underline}}
.hero{{background:linear-gradient(140deg,#7a0010 0%,#c1121f 55%,#e63946 100%);color:#fff;padding:28px 20px 0}}
.hero-head{{display:flex;align-items:center;gap:12px;margin-bottom:18px}}
.logo-box{{width:42px;height:42px;background:#fff;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#c1121f;flex-shrink:0}}
.hero-co-sub{{font-size:11px;opacity:.7;letter-spacing:.5px;text-transform:uppercase}}
.hero-co-name{{font-size:14px;font-weight:600}}
.hero-no{{font-size:28px;font-weight:600;letter-spacing:-.5px}}
.hero-proj{{font-size:14px;opacity:.8;margin-top:2px}}
.hero-chips{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}
.chip{{display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.2);border-radius:20px;padding:4px 10px;font-size:12px}}
.chip.green{{background:rgba(74,222,128,.2);border-color:rgba(74,222,128,.35)}}
.vdot{{width:6px;height:6px;border-radius:50%;background:#4ade80;display:inline-block;flex-shrink:0}}
nav{{display:flex;gap:0;margin-top:16px;border-top:1px solid rgba(255,255,255,.15)}}
nav a{{flex:1;padding:10px 4px 12px;text-align:center;font-size:13px;color:rgba(255,255,255,.75);text-decoration:none;border-bottom:2px solid transparent}}
nav a:hover{{color:#fff;border-bottom-color:rgba(255,255,255,.5);text-decoration:none}}
.wrap{{max-width:720px;margin:0 auto;padding:0 0 60px}}
.sec{{background:#fff;border:1px solid #e5e5e5;border-radius:12px;margin:16px 14px 0;padding:20px 22px;scroll-margin-top:16px}}
.sec-title{{font-size:11px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px}}
.sec-sub{{font-size:13px;color:#666;margin-bottom:12px}}
.kd-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px}}
.kd-item{{}}
.kd-lbl{{font-size:11px;color:#888;margin-bottom:2px}}
.kd-val{{font-size:14px;color:#1a1a1a}}
.kd-val a{{color:#c1121f}}
.intro-text{{font-size:14px;color:#333;line-height:1.75}}
.pos-item{{border-bottom:1px solid #eee;padding:14px 0}}
.pos-item:first-of-type{{padding-top:0}}
.pos-item:last-of-type{{border-bottom:none;padding-bottom:0}}
.pos-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px}}
.pos-name{{font-size:14px;font-weight:600;color:#1a1a1a}}
.pos-sub{{font-size:11px;color:#888;margin-top:2px}}
.pos-tags{{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}}
.tag{{font-size:10px;padding:2px 7px;border-radius:20px;background:#f3f4f6;color:#555;border:1px solid #e5e7eb}}
.tag-opt{{background:#fef3c7;color:#92400e;border-color:#fde68a}}
.tag-disc{{background:#dcfce7;color:#166534;border-color:#bbf7d0}}
.pos-prices{{text-align:right;flex-shrink:0}}
.pos-price{{font-size:15px;font-weight:600;color:#1a1a1a}}
.pos-optional{{color:#888;text-decoration:line-through}}
.pos-orig{{font-size:11px;color:#888;text-decoration:line-through;margin-top:1px}}
.pos-desc{{font-size:13px;color:#555;line-height:1.65;margin-top:4px}}
.sum-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}}
.sum-box{{background:#f9f9f9;border-radius:8px;padding:14px 16px}}
.sum-box-lbl{{font-size:11px;color:#888;margin-bottom:4px}}
.sum-box-val{{font-size:22px;font-weight:600}}
.sum-box-val.red{{color:#c1121f}}
.sum-box-sub{{font-size:11px;color:#888;margin-top:2px}}
.sum-row{{display:flex;justify-content:space-between;font-size:13px;padding:6px 0;border-bottom:1px solid #eee}}
.sum-row:last-child{{border-bottom:none}}
.sum-row.green span{{color:#166534}}
.sum-row.total{{font-size:15px;font-weight:600;border-top:1.5px solid #ccc;padding-top:10px;margin-top:4px}}
.sum-row.total span:last-child{{color:#c1121f}}
.sum-lbl{{color:#555}}
.lc-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:6px}}
.lc{{background:#f9f9f9;border:1px solid #e5e5e5;border-radius:8px;padding:14px;text-align:center}}
.lc-hi{{border-color:#c1121f;background:rgba(193,18,31,.04)}}
.lc-mo{{font-size:11px;color:#888;margin-bottom:4px}}
.lc-rate{{font-size:20px;font-weight:600;color:#1a1a1a}}
.lc-sub{{font-size:11px;color:#888;margin-top:2px}}
.lc-badge{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:20px;margin-top:6px;background:rgba(193,18,31,.1);color:#a50f18;font-weight:600}}
.fn{{font-size:11px;color:#888;margin-top:8px}}
.doc-item{{display:flex;align-items:center;gap:12px;padding:10px 12px;background:#f9f9f9;border:1px solid #e5e5e5;border-radius:8px;margin-bottom:8px}}
.doc-icon{{font-size:24px;flex-shrink:0}}
.doc-info{{flex:1}}
.doc-name{{font-size:13px;font-weight:500}}
.doc-dl{{font-size:12px;color:#c1121f;white-space:nowrap;border:1px solid #c1121f;border-radius:6px;padding:4px 10px}}
.doc-dl:hover{{background:#fff0f0;text-decoration:none}}
.pdf-frame{{border:1px solid #e5e5e5;border-radius:8px;overflow:hidden;margin-bottom:12px;height:400px}}
.pdf-frame iframe{{width:100%;height:100%;border:none;display:block}}
.order-box{{background:linear-gradient(140deg,#7a0010,#c1121f);border-radius:12px;margin:16px 14px 0;padding:28px 22px;color:#fff}}
.order-title{{font-size:20px;font-weight:600;margin-bottom:6px}}
.order-sub{{font-size:13px;opacity:.8;margin-bottom:20px;line-height:1.65}}
.order-meta{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}}
.om-box{{background:rgba(255,255,255,.12);border-radius:8px;padding:12px 14px}}
.om-lbl{{font-size:10px;opacity:.7;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}}
.om-val{{font-size:15px;font-weight:600}}
.order-btn{{display:block;width:100%;background:#fff;color:#c1121f;border:none;border-radius:9px;padding:14px;font-size:16px;font-weight:600;cursor:pointer;text-align:center;text-decoration:none}}
.order-btn:hover{{background:#fff5f5;text-decoration:none}}
.contact-strip{{margin-top:20px;padding-top:18px;border-top:1px solid rgba(255,255,255,.2)}}
.cr{{font-size:13px;opacity:.85;margin-bottom:6px}}
.footer{{text-align:center;padding:20px 14px 0;font-size:11px;color:#aaa}}
@media(max-width:500px){{
  .kd-grid{{grid-template-columns:1fr}}
  .lc-grid{{grid-template-columns:1fr}}
  .sum-grid{{grid-template-columns:1fr}}
  .order-meta{{grid-template-columns:1fr}}
  nav a{{font-size:11px}}
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="hero-head">
      <div class="logo-box">S</div>
      <div>
        <div class="hero-co-sub">{_e(provider_name)}</div>
        <div class="hero-co-name">Ihr persönliches Angebot</div>
      </div>
    </div>
    <div class="hero-no">{_e(offer_no)}</div>
    {f'<div class="hero-proj">{_e(project_name)} &middot; {_e(customer)}</div>' if project_name else f'<div class="hero-proj">{_e(customer)}</div>'}
    <div class="hero-chips">
      {f'<span class="chip green"><span class="vdot"></span> Gültig bis {_e(valid_date)}</span>' if valid_date else ""}
      {f'<span class="chip">&#128197; {_e(date_created)}</span>' if date_created else ""}
    </div>
    <nav>
      {nav_links}
    </nav>
  </div>

  <div class="sec">
    <div class="sec-title">&#127968; Empfänger</div>
    <div class="kd-grid">
      <div class="kd-item"><div class="kd-lbl">Firma</div><div class="kd-val">{_e(customer)}</div></div>
      {f'<div class="kd-item"><div class="kd-lbl">Ansprechpartner</div><div class="kd-val">{_e(contact_name)}</div></div>' if contact_name else ""}
      {email_row}
      {project_row}
      {billing_row}
      {delivery_row}
    </div>
  </div>

  <div class="sec" id="positionen">
    <div class="sec-title">&#128221; Positionen</div>
    {pos_html}

    <div style="margin-top:16px;padding-top:14px;border-top:1px solid #eee">
      <div class="sum-grid">
        <div class="sum-box">
          <div class="sum-box-lbl">Einmalig netto</div>
          <div class="sum-box-val red">{_money(one_time)}</div>
          {f'<div class="sum-box-sub">inkl. {int(discount_pct) if discount_pct == int(discount_pct) else discount_pct} % Rabatt</div>' if discount_pct > 0 else ""}
        </div>
        {f'<div class="sum-box"><div class="sum-box-lbl">Monatlich</div><div class="sum-box-val">{_money(monthly)}</div><div class="sum-box-sub">/ Monat, netto</div></div>' if monthly > 0 else ""}
      </div>
      {sum_rows}
    </div>
  </div>

  {leasing_section}

  {docs_section}

  <div class="order-box" id="bestellen">
    <div class="order-title">Angebot annehmen</div>
    <div class="order-sub">
      Mit einem Klick beauftragen Sie uns rechtsverbindlich gemäß diesem Angebot.
      Sie erhalten umgehend eine Auftragsbestätigung per E-Mail.
      {f'<br><br>Gültig bis <strong>{_e(valid_date)}</strong>' if valid_date else ""}
    </div>
    <div class="order-meta">
      <div class="om-box"><div class="om-lbl">Gesamtsumme</div><div class="om-val">{_money(one_time)}</div></div>
      <div class="om-box"><div class="om-lbl">Angebotsnummer</div><div class="om-val">{_e(offer_no)}</div></div>
    </div>
    <a href="{mailto_href}" class="order-btn">&#10003; Jetzt verbindlich bestellen</a>
    <div class="contact-strip">
      {provider_contact_html}
    </div>
  </div>

  <div class="footer">{_e(provider_name)} &middot; Dieses Angebot wurde individuell für {_e(customer)} erstellt &middot; {_e(offer_no)}</div>
</div>
</body>
</html>"""
