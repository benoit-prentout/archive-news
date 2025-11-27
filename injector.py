import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuration de la page
st.set_page_config(page_title="Newsletter Injector", page_icon="💉")

st.title("💉 Injecteur de Newsletter")
st.markdown("Cet outil permet d'envoyer manuellement du HTML brut à votre archive.")

# Récupération des secrets
default_user = st.secrets["GMAIL_USER"] if "GMAIL_USER" in st.secrets else ""
default_pass = st.secrets["GMAIL_PASSWORD"] if "GMAIL_PASSWORD" in st.secrets else ""

with st.form("email_form"):
    col1, col2 = st.columns(2)
    with col1:
        user_email = st.text_input("Votre Gmail (Expéditeur)", value=default_user)
        app_password = st.text_input("Mot de passe d'application", type="password", value=default_pass)
    
    with col2:
        dest_email = st.text_input("Envoyer à (Adresse Archive)", value=default_user)
    
    st.write("---")
    subject = st.text_input("Sujet de la Newsletter")
    
    # NOUVEAU CHAMP : URL de base pour réparer les liens relatifs
    base_url = st.text_input("URL d'origine (Recommandé)", placeholder="ex: https://newsletter.com/view/12345", 
                             help="Collez ici l'adresse de la page web où vous avez pris le HTML. Cela permet de réparer les images cassées (liens relatifs).")
    
    html_content = st.text_area("Collez le Code HTML (OuterHTML) ici", height=300)
    
    submitted = st.form_submit_button("🚀 Envoyer l'archive")

if submitted:
    if not user_email or not app_password or not subject or not html_content:
        st.error("Veuillez remplir tous les champs obligatoires.")
    else:
        try:
            with st.spinner("Traitement du HTML et envoi..."):
                
                # --- ÉTAPE DE NETTOYAGE DU HTML ---
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 1. Gestion du Lazy Loading (data-src -> src)
                for img in soup.find_all("img"):
                    if img.get("data-src") and not img.get("src"):
                        img["src"] = img["data-src"]
                    # Parfois le src existe mais est un pixel vide
                    elif img.get("data-src"):
                        img["src"] = img["data-src"]

                # 2. Conversion des liens relatifs en absolus
                if base_url:
                    # Corriger les images
                    for img in soup.find_all("img", src=True):
                        img["src"] = urljoin(base_url, img["src"])
                    # Corriger les liens cliquables
                    for a in soup.find_all("a", href=True):
                        a["href"] = urljoin(base_url, a["href"])
                
                final_html = str(soup)
                # ----------------------------------

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = user_email
                msg["To"] = dest_email
                
                # On envoie le HTML nettoyé
                part = MIMEText(final_html, "html")
                msg.attach(part)
                
                # Envoi SMTP
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(user_email, app_password)
                server.sendmail(user_email, dest_email, msg.as_string())
                server.quit()
                
            st.success(f"✅ Newsletter '{subject}' envoyée avec succès ! (Images corrigées)")
            st.balloons()
            
        except Exception as e:
            st.error(f"Erreur lors de l'envoi : {e}")