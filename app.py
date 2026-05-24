import streamlit as st
import pandas as pd

# Configuration de la page
st.set_page_config(
    page_title="Coworking Paris",
    page_icon="🏢",
    layout="wide"
)

# Titre principal
st.title("🏢 Analyse des espaces de coworking à Paris")

st.write("""
Cette application permet d’analyser des espaces de coworking à Paris à partir de données collectées automatiquement.
Elle aide l’utilisateur à comparer les lieux selon leur adresse, leur présence digitale, leurs réseaux sociaux et leurs moyens de contact.
""")

# Chargement des données
df = pd.read_excel("coworking_paris.xlsx")

# Nettoyage léger
df = df.drop_duplicates()
df = df.fillna("")

# Sidebar
st.sidebar.title("Filtres")

recherche = st.sidebar.text_input("Rechercher un coworking")

filtre_site = st.sidebar.checkbox("Afficher seulement ceux avec un site web")
filtre_linkedin = st.sidebar.checkbox("Afficher seulement ceux avec LinkedIn")
filtre_facebook = st.sidebar.checkbox("Afficher seulement ceux avec Facebook")
filtre_telephone = st.sidebar.checkbox("Afficher seulement ceux avec téléphone")

# Filtres
df_filtre = df.copy()

if recherche:
    df_filtre = df_filtre[
        df_filtre["titre"].str.contains(recherche, case=False, na=False)
    ]

if filtre_site:
    df_filtre = df_filtre[df_filtre["site"] != ""]

if filtre_linkedin:
    df_filtre = df_filtre[df_filtre["linkedin"] != ""]

if filtre_facebook:
    df_filtre = df_filtre[df_filtre["facebook"] != ""]

if filtre_telephone:
    df_filtre = df_filtre[df_filtre["telephone"] != ""]

# Indicateurs clés
st.subheader("📊 Indicateurs clés")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Coworkings", len(df_filtre))

with col2:
    st.metric("Avec site web", (df_filtre["site"] != "").sum())

with col3:
    st.metric("Avec LinkedIn", (df_filtre["linkedin"] != "").sum())

with col4:
    st.metric("Avec téléphone", (df_filtre["telephone"] != "").sum())

# Tableau principal
st.subheader("📍 Liste des espaces de coworking")

colonnes_utiles = [
    "titre",
    "adresse",
    "telephone",
    "site",
    "linkedin",
    "facebook",
    "twitter"
]

st.dataframe(df_filtre[colonnes_utiles], use_container_width=True)

# Présence digitale
st.subheader("🌐 Présence digitale des coworkings")

stats = pd.DataFrame({
    "Canal": ["Site web", "LinkedIn", "Facebook", "Twitter", "Téléphone"],
    "Nombre": [
        (df_filtre["site"] != "").sum(),
        (df_filtre["linkedin"] != "").sum(),
        (df_filtre["facebook"] != "").sum(),
        (df_filtre["twitter"] != "").sum(),
        (df_filtre["telephone"] != "").sum()
    ]
})

st.bar_chart(stats.set_index("Canal"))

# Analyse automatique
st.subheader("🧠 Analyse automatique")

total = len(df_filtre)

if total > 0:
    pourcentage_site = round((df_filtre["site"] != "").sum() / total * 100, 1)
    pourcentage_linkedin = round((df_filtre["linkedin"] != "").sum() / total * 100, 1)
    pourcentage_telephone = round((df_filtre["telephone"] != "").sum() / total * 100, 1)

    st.write(f"{pourcentage_site}% des coworkings affichés possèdent un site web.")
    st.write(f"{pourcentage_linkedin}% des coworkings affichés possèdent une page LinkedIn.")
    st.write(f"{pourcentage_telephone}% des coworkings affichés indiquent un numéro de téléphone.")
else:
    st.warning("Aucun résultat ne correspond aux filtres sélectionnés.")

# Score digital
st.subheader("⭐ Classement des coworkings les plus complets")

df_score = df_filtre.copy()

df_score["score_digital"] = (
    (df_score["site"] != "").astype(int)
    + (df_score["linkedin"] != "").astype(int)
    + (df_score["facebook"] != "").astype(int)
    + (df_score["twitter"] != "").astype(int)
    + (df_score["telephone"] != "").astype(int)
)

classement = df_score.sort_values("score_digital", ascending=False)

st.write("""
Le score digital permet d’identifier les espaces de coworking les plus faciles à contacter et les plus visibles en ligne.
Plus le score est élevé, plus le coworking possède de canaux de communication.
""")

st.dataframe(
    classement[["titre", "adresse", "site", "linkedin", "facebook", "telephone", "score_digital"]],
    use_container_width=True
)

# Détails
st.subheader("🔎 Détail des coworkings")

for index, row in df_filtre.iterrows():
    with st.expander(row["titre"]):
        st.write("**Description :**")
        st.write(row["description"])

        st.write("**Adresse :**", row["adresse"])
        st.write("**Téléphone :**", row["telephone"])

        if row["site"]:
            st.markdown(f"[🌐 Site web]({row['site']})")

        if row["linkedin"]:
            st.markdown(f"[LinkedIn]({row['linkedin']})")

        if row["facebook"]:
            st.markdown(f"[Facebook]({row['facebook']})")

        if row["twitter"]:
            st.markdown(f"[Twitter]({row['twitter']})")

# Conclusion
st.subheader("✅ Conclusion")

st.write("""
Cette application montre que la présence digitale est un critère important pour comparer les espaces de coworking.
Un utilisateur peut ainsi identifier rapidement les lieux les plus visibles, les plus accessibles et les plus simples à contacter.
""")