import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

# Configuration de la page
st.set_page_config(page_title="Newsletter Injector", page_icon="💉")

st.title("💉 Injecteur de Newsletter (Version +)")
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
    
    # URL de base indispensable pour La Redoute
    base_url = st.text_input("URL d'origine (Recommandé)", placeholder="ex: https://m12.news.laredoute.fr/...", 
                             help="Collez ici l'adresse de la page web. Indispensable pour que les liens fonctionnent.")
    
    html_content = st.text_area("Collez le Code HTML (OuterHTML) ici", height=300)
    
    submitted = st.form_submit_button("🚀 Envoyer l'archive")

if submitted:
    if not user_email or not app_password or not subject or not html_content:
        st.error("Veuillez remplir tous les champs obligatoires.")
    else:
        try:
            with st.spinner("Traitement du HTML (Nettoyage avancé)..."):
                
                soup = BeautifulSoup(html_content, "html.parser")
                
                # --- ÉTAPE 1 : GESTION AVANCÉE DU LAZY LOADING ---
                # On liste les attributs potentiels utilisés par les sites comme La Redoute
                lazy_attrs = ['data-src', 'data-original', 'data-lazy', 'data-url']
                
                for img in soup.find_all("img"):
                    # 1. Vérifier les attributs lazy loading connus
                    found_lazy = False
                    for attr in lazy_attrs:
                        if img.get(attr):
                            img['src'] = img[attr]
                            found_lazy = True
                            # On nettoie l'attribut pour éviter les conflits
                            del img[attr]
                            break
                    
                    # 2. Gestion du SRCSET (Souvent problématique en mail)
                    # Si pas de src ou si on a forcé le lazy, on regarde srcset
                    if img.get('srcset'):
                        # On prend la première URL du srcset (souvent la version mobile/standard)
                        # Format srcset: "url1 1x, url2 2x" -> on split par espace et virgule
                        first_url = img['srcset'].split(',')[0].split(' ')[0]
                        if not img.get('src') or found_lazy:
                            img['src'] = first_url
                        del img['srcset'] # On supprime srcset pour forcer le client mail à utiliser src

                # --- ÉTAPE 2 : RÉPARATION DES LIENS RELATIFS ---
                if base_url:
                    # 1. Balises IMG (src)
                    for img in soup.find_all("img", src=True):
                        # Si l'image commence par // (protocole relatif), on ajoute https:
                        if img["src"].startswith("//"):
                            img["src"] = "https:" + img["src"]
                        else:
                            img["src"] = urljoin(base_url, img["src"])

                    # 2. Balises A (href)
                    for a in soup.find_all("a", href=True):
                        a["href"] = urljoin(base_url, a["href"])
                    
                    # 3. Attributs BACKGROUND (tableaux, td, body)
                    for tag in soup.find_all(True, background=True):
                        tag["background"] = urljoin(base_url, tag["background"])

                    # 4. Styles CSS Inline (background-image: url(...))
                    # C'est complexe, on utilise une regex simple pour trouver url('...')
                    for tag in soup.find_all(style=True):
                        style = tag['style']
                        if 'url(' in style:
                            # Fonction pour remplacer l'URL dans le CSS
                            def replace_css_url(match):
                                url_content = match.group(1).strip("'").strip('"')
                                if url_content.startswith("//"):
                                    new_url = "https:" + url_content
                                else:
                                    new_url = urljoin(base_url, url_content)
                                return f"url('{new_url}')"
                            
                            # Regex qui cherche url( ... )
                            new_style = re.sub(r"url\((.*?)\)", replace_css_url, style)
                            tag['style'] = new_style

                final_html = str(soup)

                # Construction de l'email
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = user_email
                msg["To"] = dest_email
                
                part = MIMEText(final_html, "html")
                msg.attach(part)
                
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(user_email, app_password)
                server.sendmail(user_email, dest_email, msg.as_string())
                server.quit()
                
            st.success(f"✅ Newsletter '{subject}' envoyée ! (Compatibilité La Redoute activée)")
            st.balloons()
            
        except Exception as e:
            st.error(f"Erreur lors de l'envoi : {e}")
