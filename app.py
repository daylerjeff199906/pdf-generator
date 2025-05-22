from flask import Flask, request, jsonify, send_file, render_template, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from io import BytesIO
import requests
from datetime import datetime
from PIL import Image as PILImage
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:9000"}})

API_BASE = 'https://api.vertebrados.iiap.gob.pe/api/v1/individuals/'

def safe_get(d, keys, default=None):
    for key in keys:
        if not d or not isinstance(d, dict):
            return default
        d = d.get(key)
    return d if d is not None else default

def create_amphibian_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Estilos de texto
    styles = getSampleStyleSheet()
    italic_style = ParagraphStyle('Italic', parent=styles['Normal'], fontName='Helvetica-Oblique')
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=8)
    
    # PORTADA
    c.setFont('Helvetica-Bold', 36)
    c.drawCentredString(width/2, height/2 + 100, "REGISTRO DE ESPECIMEN")
    
    scientific_name = safe_get(data, ['species', 'scientificName'], 'N/A')
    p_scientific = Paragraph(f'<i>{scientific_name}</i>', italic_style)
    p_scientific.wrapOn(c, width-2*inch, 50)
    p_scientific.drawOn(c, (width - p_scientific.width)/2, height/2)
    
    c.setFont('Helvetica', 18)
    c.drawCentredString(width/2, height/2 - 50, f"Código: {data.get('code', 'N/A')}")
    
    museum = data.get('museum', {})
    museum_info = f"{museum.get('name', '')} ({museum.get('acronym','')})" if museum else ""
    c.setFont('Helvetica', 16)
    c.drawCentredString(width/2, height/2 - 100, museum_info)
    
    c.setFont('Helvetica', 12)
    c.drawCentredString(width/2, 50, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.showPage()

    # INFORMACIÓN GENERAL
    y = height - inch
    p_title = Paragraph("INFORMACIÓN DEL ESPÉCIMEN", header_style)
    p_title.wrapOn(c, width-2*inch, 50)
    p_title.drawOn(c, inch, y)
    y -= 30
    
    # Tabla de información general
    sexo_nombre = safe_get(data, ['sex', 'name'], 'N/A')
    actividad_nombre = safe_get(data, ['activity', 'name'], 'N/A')
    bosque_nombre = safe_get(data, ['forestType', 'name'], 'N/A')
    
    info_data = [
        ["Código:", data.get('code', 'N/A')],
        ["Nombre Científico:", Paragraph(f'<i>{scientific_name}</i>', italic_style)],
        ["Nombre Común:", safe_get(data, ['species', 'commonName'], 'N/A')],
        ["Sexo:", sexo_nombre],
        ["Fecha Identificación:", f"{data.get('identDate', 'N/A')} {data.get('identTime', '')}"],
        ["Actividad:", actividad_nombre],
        ["Tipo de Bosque:", bosque_nombre]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    info_table.wrapOn(c, width-2*inch, height)
    info_table.drawOn(c, inch, y - info_table._height)
    y -= info_table._height + 30
    
    # CLASIFICACIÓN TAXONÓMICA
    p_section = Paragraph("CLASIFICACIÓN TAXONÓMICA", header_style)
    p_section.wrapOn(c, width-2*inch, 50)
    p_section.drawOn(c, inch, y)
    y -= 30
    
    # Tabla taxonómica
    cls = safe_get(data, ['species', 'genus', 'family', 'order', 'class'], {})
    tax_data = [
        ["Clase:", cls.get('name', 'N/A')],
        ["Orden:", safe_get(data, ['species', 'genus', 'family', 'order', 'name'], 'N/A')],
        ["Familia:", safe_get(data, ['species', 'genus', 'family', 'name'], 'N/A')],
        ["Género:", safe_get(data, ['species', 'genus', 'name'], 'N/A')],
        ["Especie:", Paragraph(f'<i>{scientific_name}</i>', italic_style)]
    ]
    
    tax_table = Table(tax_data, colWidths=[1.5*inch, 4.5*inch])
    tax_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    tax_table.wrapOn(c, width-2*inch, height)
    tax_table.drawOn(c, inch, y - tax_table._height)
    y -= tax_table._height + 30
    
    # UBICACIÓN GEOGRÁFICA
    p_section = Paragraph("UBICACIÓN GEOGRÁFICA", header_style)
    p_section.wrapOn(c, width-2*inch, 50)
    p_section.drawOn(c, inch, y)
    y -= 30
    
    # Tabla de ubicación
    ev = safe_get(data, ['ocurrence', 'event'], {})
    loc = ev.get('locality', {})
    dist = loc.get('district', {})
    prov = dist.get('province', {})
    dept = prov.get('department', {})
    country = dept.get('country', {})
    
    loc_data = [
        ["País:", country.get('name', 'N/A')],
        ["Departamento:", dept.get('name', 'N/A')],
        ["Provincia:", prov.get('name', 'N/A')],
        ["Distrito:", dist.get('name', 'N/A')],
        ["Localidad:", loc.get('name', 'N/A')],
        ["Coordenadas:", f"Lat {ev.get('latitude', 'N/A')}, Long {ev.get('longitude', 'N/A')}"]
    ]
    
    loc_table = Table(loc_data, colWidths=[1.5*inch, 4.5*inch])
    loc_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    loc_table.wrapOn(c, width-2*inch, height)
    loc_table.drawOn(c, inch, y - loc_table._height)
    y -= loc_table._height + 30
    
    # IDENTIFICADORES
    identifiers = data.get('identifiers', [])
    if identifiers:
        p_section = Paragraph("IDENTIFICADORES", header_style)
        p_section.wrapOn(c, width-2*inch, 50)
        p_section.drawOn(c, inch, y)
        y -= 30
        
        id_data = []
        for idf in identifiers:
            p = idf.get('person', {})
            name = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip()
            email = p.get('email', '')
            id_data.append([name, email])
        
        id_table = Table(id_data, colWidths=[3*inch, 3*inch])
        id_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        id_table.wrapOn(c, width-2*inch, height)
        id_table.drawOn(c, inch, y - id_table._height)
        y -= id_table._height + 30
    
    # IMÁGENES
    imgs = safe_get(data, ['files', 'images'], [])
    if imgs:
        c.showPage()
        y = height - inch
        p_title = Paragraph("IMÁGENES DEL ESPÉCIMEN", header_style)
        p_title.wrapOn(c, width-2*inch, 50)
        p_title.drawOn(c, inch, y)
        y -= 30
        
        for im in imgs:
            try:
                r = requests.get(im['name'], timeout=10)
                r.raise_for_status()
                buf = BytesIO(r.content)
                with PILImage.open(buf) as img:
                    iw, ih = img.size
                    ar = iw/ih
                    dw = width - 2*inch  # Usar todo el ancho disponible
                    dh = dw/ar
                    
                    if y - dh - 100 < 0.5*inch:  # Verificar espacio en página
                        c.showPage()
                        y = height - inch
                        p_title = Paragraph("IMÁGENES DEL ESPÉCIMEN (cont.)", header_style)
                        p_title.wrapOn(c, width-2*inch, 50)
                        p_title.drawOn(c, inch, y)
                        y -= 30
                    
                    # Título de la imagen
                    p_img_title = Paragraph(f"<b>Imagen {im.get('order', '')}</b>", section_style)
                    p_img_title.wrapOn(c, width-2*inch, 50)
                    p_img_title.drawOn(c, inch, y)
                    y -= 20
                    
                    # Metadatos
                    meta = []
                    if im.get('format'): meta.append(f"Formato: {im['format']}")
                    if im.get('size'): meta.append(f"Tamaño: {im['size']} bytes")
                    if im.get('note'): meta.append(f"Nota: {im['note']}")
                    
                    if meta:
                        c.setFont('Helvetica', 9)
                        c.drawString(inch, y, " | ".join(meta))
                        y -= 20
                    
                    # Dibujar imagen
                    buf.seek(0)
                    image = ImageReader(buf)
                    c.drawImage(image, inch, y-dh, width=dw, height=dh, preserveAspectRatio=True)
                    y -= dh + 40
                    
            except Exception as e:
                c.setFont('Helvetica', 10)
                c.drawString(inch, y, f"Error al cargar imagen: {e}")
                y -= 20

    c.save()
    buffer.seek(0)
    return buffer, scientific_name.replace(" ", "_")

@app.route('/generate-pdf-from-data', methods=['POST'])
def generate_pdf_from_data():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No se recibió contenido JSON"}), 400
        
        pdf, filename = create_amphibian_pdf(data)
        response = make_response(pdf.read())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', f'attachment; filename=registro_{filename}.pdf')
        return response
    except Exception as e:
        return jsonify({"error": f"Error al generar PDF: {e}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)