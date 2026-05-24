import os
import re
import json
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import pandas as pd


SEED_URL = "https://www.leportagesalarial.com/coworking/"
OUTPUT_XLSX = "coworking_paris.xlsx"

REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_REQ = 0

# BONUS: Serper.dev (optionnel)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")  # export SERPER_API_KEY="..."
SERPER_ENDPOINT = "https://google.serper.dev/search"


session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
})


def fetch(url: str) -> str:
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def abs_url(base: str, href: str) -> str:
    return urljoin(base, (href or "").strip())


def text_clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def meta(soup: BeautifulSoup, *, name: str = None, prop: str = None) -> str:
    if name:
        t = soup.find("meta", attrs={"name": name})
        if t and t.get("content"):
            return t["content"].strip()
    if prop:
        t = soup.find("meta", attrs={"property": prop})
        if t and t.get("content"):
            return t["content"].strip()
    return ""


def get_title_tag(soup: BeautifulSoup) -> str:
    return soup.title.get_text(" ", strip=True) if soup.title else ""


def get_h1(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    return h1.get_text(" ", strip=True) if h1 else ""


def get_main_image(soup: BeautifulSoup, page_url: str) -> str:
    # og:image puis twitter:image puis 1ère image
    og = meta(soup, prop="og:image")
    if og:
        return abs_url(page_url, og)

    tw = meta(soup, name="twitter:image")
    if tw:
        return abs_url(page_url, tw)

    img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src") or ""
        if src:
            return abs_url(page_url, src)
    return ""


def get_description(soup: BeautifulSoup) -> str:
    md = meta(soup, name="description")
    if md:
        return md

    ogd = meta(soup, prop="og:description")
    if ogd:
        return ogd

    # fallback: premier paragraphe un peu long
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if t and len(t) >= 80:
            return t
    return ""


def extract_paris_urls(seed_url: str) -> List[str]:
    """
    Récupère les liens de coworking dans la section:
    'Coworking Paris – Île de France :'
    jusqu'au prochain h3.
    """
    html = fetch(seed_url)
    soup = soupify(html)

    # repère le H3 "Coworking Paris – Île de France"
    h3_paris = None
    for h3 in soup.find_all(["h2", "h3"]):
        if "coworking paris" in h3.get_text(" ", strip=True).lower():
            h3_paris = h3
            break

    if not h3_paris:
        raise RuntimeError("Section 'Coworking Paris – Île de France' introuvable sur la page.")

    urls = []
    # on parcourt les éléments suivants jusqu'au prochain h3/h2
    node = h3_paris.find_next_sibling()
    while node:
        if node.name in ["h2", "h3"]:
            break
        # dans cette zone il y a une liste <ul><li><a ...>
        for a in node.find_all("a", href=True):
            u = abs_url(seed_url, a["href"])
            # garde uniquement les pages /coworking/.../ (fiches)
            if "/coworking/" in urlparse(u).path and u.rstrip("/") != seed_url.rstrip("/"):
                urls.append(u)
        node = node.find_next_sibling()

    # dédoublonnage conservant l’ordre
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_contact_block(soup: BeautifulSoup, page_url: str) -> Dict[str, str]:
    """
    Sur les fiches, on a généralement:
    ## Contacter ...
      * Adresse : ...
      * Téléphone : ...
      * Accès : ...
      * Site : <a ...>
      * Twitter : <a ...>
      * Facebook : <a ...>
      * LinkedIn : <a ...>
    """
    data = {
        "adresse": "",
        "telephone": "",
        "acces": "",
        "site": "",
        "twitter": "",
        "facebook": "",
        "linkedin": "",
    }

    # Cherche une zone contenant "Contacter"
    heading = None
    for h in soup.find_all(["h2", "h3"]):
        if "contacter" in h.get_text(" ", strip=True).lower():
            heading = h
            break

    if not heading:
        return data

    # Collecte des <li> juste après ce heading
    lis = []
    node = heading.find_next_sibling()
    # souvent la liste n'est pas forcément un <ul> direct, donc on collecte un peu
    for _ in range(0, 6):
        if not node:
            break
        lis.extend(node.find_all("li"))
        node = node.find_next_sibling()

    def parse_li(li_text: str, li_tag) -> Tuple[str, str]:
        t = text_clean(li_text)
        # split sur ":" si présent
        if ":" in t:
            k, v = t.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
        else:
            return "", ""

        # si lien présent (site/social), on récupère l'href
        a = li_tag.find("a", href=True)
        href = abs_url(page_url, a["href"]) if a else ""

        if "adresse" in k:
            return "adresse", v
        if "téléphone" in k or "telephone" in k:
            return "telephone", v
        if "accès" in k or "acces" in k:
            return "acces", v
        if "site" in k:
            return "site", href or v
        if "twitter" in k:
            return "twitter", href or v
        if "facebook" in k:
            return "facebook", href or v
        if "linkedin" in k:
            return "linkedin", href or v

        return "", ""

    for li in lis:
        t = li.get_text(" ", strip=True)
        k, v = parse_li(t, li)
        if k and v and not data[k]:
            data[k] = v

    return data


def extract_published_date(soup: BeautifulSoup) -> str:
    # 1) meta article:published_time
    dt = meta(soup, prop="article:published_time")
    if dt:
        return dt

    # 2) <time datetime="">
    t = soup.find("time", attrs={"datetime": True})
    if t:
        return t["datetime"].strip()

    # 3) JSON-LD datePublished
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue

        def walk(obj):
            if isinstance(obj, dict):
                if obj.get("datePublished"):
                    return str(obj["datePublished"]).strip()
                for v in obj.values():
                    got = walk(v)
                    if got:
                        return got
            elif isinstance(obj, list):
                for it in obj:
                    got = walk(it)
                    if got:
                        return got
            return ""

        got = walk(data)
        if got:
            return got

    # 4) fallback WordPress: "was last modified: ..."
    page_text = soup.get_text("\n", strip=True)
    m = re.search(r"was last modified:\s*(.+?)\s+by\b", page_text, flags=re.I)
    if m:
        return text_clean(m.group(1))

    return ""


def serper_enrich(url: str) -> Dict[str, str]:
    """
    BONUS: récupère title/snippet (SERP).
    Serper ne renvoie pas "meta title/meta description" HTML, mais le titre/snippet Google,
    souvent très proche de ce que tu veux pour une analyse SEO.
    """
    if not SERPER_API_KEY:
        return {"serp_title": "", "serp_description": "", "serp_link": ""}

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": url, "num": 5}
    r = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    organic = data.get("organic", []) or []
    if not organic:
        return {"serp_title": "", "serp_description": "", "serp_link": ""}

    top = organic[0]
    return {
        "serp_title": (top.get("title") or "").strip(),
        "serp_description": (top.get("snippet") or "").strip(),
        "serp_link": (top.get("link") or "").strip(),
    }


def extract_homepage_text(home_url: str) -> str:
    """
    BONUS: texte brut de la page d'accueil du 'site' (si présent).
    On limite la taille pour Excel.
    """
    if not home_url:
        return ""
    try:
        html = fetch(home_url)
    except Exception:
        return ""

    soup = soupify(html)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    txt = soup.get_text(" ", strip=True)
    return txt[:4000]


def scrape_coworking_page(url: str) -> Dict[str, str]:
    html = fetch(url)
    soup = soupify(html)

    meta_title = get_title_tag(soup)
    meta_description = meta(soup, name="description") or meta(soup, prop="og:description")

    h1 = get_h1(soup) or meta_title
    image = get_main_image(soup, url)
    description = get_description(soup)

    contact = extract_contact_block(soup, url)
    published = extract_published_date(soup)

    row = {
        "url": url,
        "titre": h1,
        "image_principale": image,
        "description": description,

        "adresse": contact["adresse"],
        "telephone": contact["telephone"],
        "acces": contact["acces"],
        "site": contact["site"],
        "twitter": contact["twitter"],
        "facebook": contact["facebook"],
        "linkedin": contact["linkedin"],

        "meta_title": meta_title,
        "meta_description": meta_description,
        "meta_title_lt_150": (len(meta_title) < 150 if meta_title else False),
        "date_publication": published,
    }


    return row


def main():
    paris_urls = extract_paris_urls(SEED_URL)
    print(f"✅ {len(paris_urls)} URLs Paris trouvées.")

    rows = []
    for i, u in enumerate(paris_urls, 1):
        try:
            row = scrape_coworking_page(u)
            rows.append(row)
            print(f"[{i}/{len(paris_urls)}] OK - {u}")
        except Exception as e:
            print(f"[{i}/{len(paris_urls)}] FAIL - {u} -> {e}")
        time.sleep(SLEEP_BETWEEN_REQ)

    df = pd.DataFrame(rows)
    df.to_excel(OUTPUT_XLSX, index=False)
    print(f"📦 Export XLSX terminé: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd

st.title("Espaces de coworking à Paris")

df = pd.read_excel("coworking_paris.xlsx")

st.subheader("Nombre total de coworkings")
st.write(len(df))

recherche = st.text_input("Rechercher un coworking")

if recherche:
    df = df[df["titre"].str.contains(recherche, case=False, na=False)]

st.subheader("Liste des coworkings")
st.dataframe(df[["titre", "adresse", "telephone", "site", "linkedin", "facebook"]])

st.subheader("Présence digitale")

stats = {
    "Site web": df["site"].notna().sum(),
    "LinkedIn": df["linkedin"].notna().sum(),
    "Facebook": df["facebook"].notna().sum(),
    "Twitter": df["twitter"].notna().sum()
}

st.bar_chart(stats)

st.subheader("Détail des coworkings")

for index, row in df.iterrows():
    st.markdown(f"### {row['titre']}")
    st.write(row["description"])
    st.write("📍 Adresse :", row["adresse"])
    st.write("📞 Téléphone :", row["telephone"])
    st.write("🌐 Site :", row["site"])
    st.write("---")