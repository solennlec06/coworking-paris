import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Projet Coworking Paris",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Projet Coworking : analyse des espaces à Paris")

st.write("""
L’objectif de cette application est de permettre à un utilisateur de comparer rapidement plusieurs
espaces de coworking à Paris selon leurs informations principales : adresse, contact, site web
et présence sur les réseaux sociaux.
""")

df = pd.read_excel("coworking_paris.xlsx")

df = df.drop_duplicates()
df = df.fillna("")

st.sidebar.title("🔎 Filtres de recherche")
st.sidebar.write("Ces filtres permettent de trouver plus facilement un espace adapté aux besoins de l’utilisateur.")

recherche = st.sidebar.text_input("Rechercher un coworking par nom")

filtre_site = st.sidebar.checkbox("Afficher seulement ceux avec un site web")
filtre_linkedin = st.sidebar.checkbox("Afficher seulement ceux avec LinkedIn")
filtre_facebook = st.sidebar.checkbox("Afficher seulement ceux avec Facebook")
filtre_telephone = st.sidebar.checkbox("Afficher seulement ceux avec téléphone")

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

st.subheader("📊 Indicateurs principaux")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Coworkings affichés", len(df_filtre))

with col2:
    st.metric("Avec site web", (df_filtre["site"] != "").sum())

with col3:
    st.metric("Avec LinkedIn", (df_filtre["linkedin"] != "").sum())

with col4:
    st.metric("Avec téléphone", (df_filtre["telephone"] != "").sum())

st.write("""
Ces indicateurs donnent une première vision de la qualité des informations disponibles.
Pour moi, un espace de coworking bien renseigné est plus rassurant pour un utilisateur.
""")

st.subheader("📍 Tableau des espaces de coworking")

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

st.subheader("🌐 Analyse de la présence digitale")

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

st.write("""
J’ai ajouté ce graphique pour comparer rapidement les canaux de communication utilisés par les coworkings.
Cela permet de voir quels moyens sont les plus présents : site web, téléphone ou réseaux sociaux.
""")

st.subheader("⭐ Score de visibilité digitale")

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
J’ai créé un score digital simple.  
Chaque coworking gagne 1 point lorsqu’il possède un site web, un téléphone ou un réseau social.
Ce score permet d’identifier les espaces les plus faciles à contacter et les plus visibles en ligne.
""")

st.dataframe(
    classement[["titre", "adresse", "site", "linkedin", "facebook", "telephone", "score_digital"]],
    use_container_width=True
)

st.subheader("🔎 Détail des coworkings")

st.write("""
Cette partie permet de consulter les informations plus précisément, sans afficher tout le texte directement.
J’ai choisi d’utiliser des menus déroulants pour rendre l’application plus lisible.
""")

for index, row in df_filtre.iterrows():
    with st.expander(row["titre"]):
        st.write("**Description :**")
        st.write(row["description"])

        st.write("**Adresse :**", row["adresse"])
        st.write("**Téléphone :**", row["telephone"])

        if row["site"]:
            st.markdown(f"[🌐 Visiter le site]({row['site']})")

        if row["linkedin"]:
            st.markdown(f"[LinkedIn]({row['linkedin']})")

        if row["facebook"]:
            st.markdown(f"[Facebook]({row['facebook']})")

        if row["twitter"]:
            st.markdown(f"[Twitter]({row['twitter']})")

