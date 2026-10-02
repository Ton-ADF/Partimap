import os
from pathlib import Path
import streamlit as st
from pypdf import PdfWriter
import fitz  # PyMuPDF
from pdfCropMargins import crop
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# Pagina configuratie
st.set_page_config(page_title="Bladmuziek E-reader Verwerker", page_icon="🎵", layout="centered")

def genereer_titelblad(titel_tekst, instrument_tekst, logo_pad, output_pdf):
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=100, bottomMargin=50)
    story = []
    styles = getSampleStyleSheet()
    
    titel_style = ParagraphStyle(
        'TitelStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=26, leading=32,
        alignment=TA_CENTER, spaceAfter=15
    )
    
    instrument_style = ParagraphStyle(
        'InstrumentStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=18, leading=24,
        alignment=TA_CENTER, spaceAfter=30, textColor='gray'
    )
    
    if logo_pad and os.path.exists(logo_pad):
        img = Image(logo_pad, width=140, height=140)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 30))
        
    story.append(Paragraph(titel_tekst, titel_style))
    if instrument_tekst and instrument_tekst.strip():
        story.append(Paragraph(instrument_tekst, instrument_style))
        
    doc.build(story)

def formatteer_titel(bestandsnaam):
    naam_zonder_ext = os.path.splitext(bestandsnaam)[0]
    if '-' in naam_zonder_ext:
        titel = naam_zonder_ext.rsplit('-', 1)[0]
    else:
        titel = naam_zonder_ext
    return titel.strip().replace('_', ' ')

def laad_logos():
    script_map = Path(__file__).parent
    logos = [
        f.name for f in script_map.iterdir() 
        if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg']
    ]
    return sorted(logos) if logos else []

# --- STREAMLIT INTERFACE ---
st.title("🎵 Bladmuziek E-reader Verwerker")
st.write("Upload je bladmuziek, stel je titelblad in en maak direct je geoptimaliseerde e-reader PDF aan.")

# Instellingen in de zijbalk
with st.sidebar:
    st.header("⚙️ Instellingen")
    gebruik_titelblad = st.checkbox("Voeg titelblad toe", value=True)
    titel_setlist = st.text_input("Titel setlist", value="Zomerconcert 2026")
    instrument_naam = st.text_input("Instrument", value="Viool")
    
    beschikbare_logos = laad_logos()
    gekozen_logo = st.selectbox("Selecteer Logo", options=beschikbare_logos) if beschikbare_logos else None
    marge_waarde = st.text_input("Crop marge (pixels)", value="5")

# Upload gedeelte (zonder strenge type-filter in de browser)
st.subheader("📂 Bladmuziek Bestanden")
uploaded_files = st.file_uploader(
    "Selecteer of sleep je PDF-bestanden hier naartoe", 
    accept_multiple_files=True
)

if uploaded_files:
    # Filter handmatig op PDF (ongeacht kleine/grote letters)
    pdf_files = [f for f in uploaded_files if f.name.lower().endswith('.pdf')]
    
    if not pdf_files:
        st.error("Upload alleen geldige PDF-bestanden!")
    else:
        st.success(f"Er zijn {len(pdf_files)} geldige PDF-bestanden geselecteerd!")
        
    for f in pdf_files:
            st.write(f"📄 {f.name} ({f.size} bytes)")
        
    if st.button("🚀 Crop & Maak E-reader PDF", type="primary"):
            # (Hieronder blijft de rest van je verwerkingscode hetzelfde)

    
    # Toon een lijstje van wat er geüpload is
    for f in uploaded_files:
        st.write(f"📄 {f.name} ({f.size} bytes)")
        progress_bar = st.progress(0)
        status_text = st.empty()
        tijdelijke_bestanden = []
        output_pdf_pad = "e_reader_setlist.pdf"
        
        try:
            writer = PdfWriter()
            huidige_pagina_teller = 0
            titelblad_ruw = "temp_titelblad_ruw.pdf"
            titelblad_cropped = "temp_titelblad_cropped.pdf"

            if gebruik_titelblad:
                status_text.text("Bezig met genereren en croppen van titelblad...")
                logo_pad = os.path.join(Path(__file__).parent, gekozen_logo) if gekozen_logo else ""
                genereer_titelblad(titel_setlist, instrument_naam, logo_pad, titelblad_ruw)
                tijdelijke_bestanden.append(titelblad_ruw)

                crop([
                    titelblad_ruw,
                    "-o", titelblad_cropped,
                    "-p", marge_waarde.strip(),
                    "-u",
                    "-s"
                ], quiet=True, string_io=True)

                if os.path.exists(titelblad_cropped):
                    tijdelijke_bestanden.append(titelblad_cropped)
                    gebruikte_titelblad_pdf = titelblad_cropped
                else:
                    gebruikte_titelblad_pdf = titelblad_ruw

                writer.append(gebruikte_titelblad_pdf)
                writer.add_outline_item(title=f"{titel_setlist} - {instrument_naam}" if instrument_naam else titel_setlist, page_number=huidige_pagina_teller)
                huidige_pagina_teller += 1

            totaal = len(uploaded_files)
            for index, uploaded_file in enumerate(uploaded_files):
                stuk_naam = formatteer_titel(uploaded_file.name)
                status_text.text(f"Bezig met croppen ({index+1}/{totaal}): {stuk_naam}")
                progress_bar.progress((index + 1) / totaal)

                temp_input_path = f"temp_input_{index}.pdf"
                with open(temp_input_path, "wb") as file_out:
                    file_out.write(uploaded_file.getbuffer())
                tijdelijke_bestanden.append(temp_input_path)

                temp_cropped_path = f"temp_cropped_{index}.pdf"
                _, _, _, stderr = crop([
                    temp_input_path,
                    "-o", temp_cropped_path,
                    "-p", marge_waarde.strip(),
                    "-u",
                    "-s"
                ], quiet=True, string_io=True)

                if not os.path.exists(temp_cropped_path) or os.path.getsize(temp_cropped_path) == 0:
                    raise Exception(f"Fout bij het croppen van {stuk_naam}. Mogelijke fout: {stderr}")

                tijdelijke_bestanden.append(temp_cropped_path)

                temp_doc = fitz.open(temp_cropped_path)
                aantal_paginas = len(temp_doc)
                temp_doc.close()

                writer.append(temp_cropped_path)
                writer.add_outline_item(title=stuk_naam, page_number=huidige_pagina_teller)
                huidige_pagina_teller += aantal_paginas

            status_text.text("Bezig met opslaan...")
            with open(output_pdf_pad, "wb") as f:
                writer.write(f)
            tijdelijke_bestanden.append(output_pdf_pad)

            status_text.text("Klaar!")
            progress_bar.progress(1.0)
            st.success("🎉 Je e-reader setlist is succesvol aangemaakt!")

            with open(output_pdf_pad, "rb") as f:
                st.download_button(
                    label="📥 Download E-reader PDF",
                    data=f,
                    file_name=f"{titel_setlist}_{instrument_naam}.pdf".replace(" ", "_"),
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Er is een technische fout opgetreden: {str(e)}")

        finally:
            for temp_file in tijdelijke_bestanden:
                if temp_file != output_pdf_pad and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
