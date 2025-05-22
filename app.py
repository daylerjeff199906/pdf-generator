from flask import Flask, request, jsonify, send_file, render_template, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
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

def draw_header(c, width, height, scientific_name):
    """Dibuja el encabezado minimalista en cada página"""
    c.setFont('Helvetica', 10)
    c.drawString(0.5*inch, height-0.5*inch, scientific_name)
    c.line(0.5*inch, height-0.6*inch, width-0.5*inch, height-0.6*inch)

def create_table(data, col_widths):
    """Crea una tabla con bordes como la de colectores"""
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    return table

def create_amphibian_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Obtener datos importantes
    scientific_name = safe_get(data, ['species', 'scientificName'], 'N/A')
    common_name = safe_get(data, ['species', 'commonName'], 'N/A')
    code = data.get('code', 'N/A')
    
      # PORTADA MEJORADA
    c.setFont('Helvetica-Bold', 40)
    c.drawCentredString(width/2, height/2 + 80, "GUÍA DE ESPECIE")
    
    c.setFont('Helvetica', 30)
    c.setFont('Helvetica-Oblique', 30)
    c.drawCentredString(width/2, height/2 + 40, scientific_name)
    c.drawCentredString(width/2, height/2, common_name)
    
    c.setFont('Helvetica', 16)
    c.drawCentredString(width/2, height/2 - 40, f"Código: {code}")
    
    # Pie de página
    c.setFont('Helvetica', 10)
    c.drawCentredString(width/2, 50, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.showPage()
    
    # INFORMACIÓN GENERAL (en tabla con bordes)
    draw_header(c, width, height, scientific_name)
    y = height - 1*inch
    
    c.setFont('Helvetica-Bold', 14)
    c.drawString(1*inch, y, "INFORMACIÓN GENERAL")
    y -= 30
    
    info_data = [
        ["Código:", code],
        ["Nombre científico:", scientific_name],
        ["Nombre común:", common_name],
        ["Sexo:", safe_get(data, ['sex', 'name'], 'N/A')],
        ["Fecha identificación:", f"{data.get('identDate', 'N/A')} {data.get('identTime', '')}"],
        ["Actividad:", safe_get(data, ['activity', 'name'], 'N/A')],
        ["Tipo de bosque:", safe_get(data, ['forestType', 'name'], 'N/A')]
    ]
    
    info_table = create_table(info_data, [2*inch, 4*inch])
    info_table.wrapOn(c, width-2*inch, height)
    info_table.drawOn(c, 1*inch, y - info_table._height)
    y -= info_table._height + 20
    
    # CLASIFICACIÓN TAXONÓMICA (en tabla con bordes)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(1*inch, y, "CLASIFICACIÓN TAXONÓMICA")
    y -= 30
    
    cls = safe_get(data, ['species', 'genus', 'family', 'order', 'class'], {})
    tax_data = [
        ["Clase:", cls.get('name', 'N/A')],
        ["Orden:", safe_get(data, ['species', 'genus', 'family', 'order', 'name'], 'N/A')],
        ["Familia:", safe_get(data, ['species', 'genus', 'family', 'name'], 'N/A')],
        ["Género:", safe_get(data, ['species', 'genus', 'name'], 'N/A')],
        ["Especie:", scientific_name]
    ]
    
    tax_table = create_table(tax_data, [1.5*inch, 4.5*inch])
    tax_table.wrapOn(c, width-2*inch, height)
    tax_table.drawOn(c, 1*inch, y - tax_table._height)
    y -= tax_table._height + 20
    
    # UBICACIÓN GEOGRÁFICA (en tabla con bordes)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(1*inch, y, "UBICACIÓN GEOGRÁFICA")
    y -= 30
    
    ev = safe_get(data, ['ocurrence', 'event'], {})
    loc = ev.get('locality', {})
    dist = loc.get('district', {})
    prov = dist.get('province', {})
    dept = prov.get('department', {})
    country = dept.get('country', {})
    
    # Obtener y redondear coordenadas a 5 decimales
    lat = ev.get('latitude', 'N/A')
    lon = ev.get('longitude', 'N/A')
    try:
        lat_str = f"{float(lat):.5f}"
    except (TypeError, ValueError):
        lat_str = 'N/A'
    try:
        lon_str = f"{float(lon):.5f}"
    except (TypeError, ValueError):
        lon_str = 'N/A'

    loc_data = [
        ["País:", country.get('name', 'N/A')],
        ["Departamento:", dept.get('name', 'N/A')],
        ["Provincia:", prov.get('name', 'N/A')],
        ["Distrito:", dist.get('name', 'N/A')],
        ["Localidad:", loc.get('name', 'N/A')],
        ["Coordenadas:", f"Lat {lat_str}, Long {lon_str}"]
    ]
    
    loc_table = create_table(loc_data, [1.5*inch, 4.5*inch])
    loc_table.wrapOn(c, width-2*inch, height)
    loc_table.drawOn(c, 1*inch, y - loc_table._height)
    y -= loc_table._height + 20
    
    # IDENTIFICADORES (en tabla con bordes)
    identifiers = data.get('identifiers', [])
    if identifiers:
        c.setFont('Helvetica-Bold', 14)
        c.drawString(1*inch, y, "IDENTIFICADORES")
        y -= 30
        
        id_data = [["Nombre", "Email"]]
        for idf in identifiers:
            p = idf.get('person', {})
            name = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip()
            email = p.get('email', '')
            id_data.append([name, email])
        
        id_table = Table(id_data, colWidths=[3*inch, 3*inch])
        id_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        id_table.wrapOn(c, width-2*inch, height)
        id_table.drawOn(c, 1*inch, y - id_table._height)
        y -= id_table._height + 20
    
 # IMÁGENES MEJORADAS (mitad superior e inferior)
    imgs = safe_get(data, ['files', 'images'], [])
    if imgs:
        c.showPage()
        draw_header(c, width, height, scientific_name)
        
        # Calcular áreas para las imágenes
        page_center = height / 2
        img_area_height = (height - 2*inch) / 2  # Mitad del espacio útil
        
        for i, im in enumerate(imgs):
            # Cambiar de página cada 2 imágenes
            if i > 0 and i % 2 == 0:
                c.showPage()
                draw_header(c, width, height, scientific_name)
                c.setFont('Helvetica-Bold', 14)
                c.drawString(1*inch, height-1*inch, "IMÁGENES DEL ESPECIMEN (continuación)")
            
            try:
                # Descargar imagen
                r = requests.get(im['name'], timeout=10)
                r.raise_for_status()
                buf = BytesIO(r.content)
                
                with PILImage.open(buf) as img:
                    iw, ih = img.size
                    ar = iw / ih
                    
                    # Determinar posición (superior o inferior)
                    if i % 2 == 0:
                        # Imagen superior
                        y_position = height - 1.5*inch - img_area_height
                        section_label = f"Imagen {i+1} (Superior)"
                    else:
                        # Imagen inferior
                        y_position = page_center - 0.5*inch - img_area_height
                        section_label = f"Imagen {i+1} (Inferior)"
                    
                    # Calcular dimensiones máximas
                    max_width = width - 2*inch
                    max_height = img_area_height - 0.8*inch  # Dejar espacio para metadata
                    
                    # Calcular dimensiones manteniendo aspecto
                    dw = min(max_width, iw)
                    dh = min(max_height, dw/ar)
                    if dh > max_height:
                        dh = max_height
                        dw = dh * ar
                    
                    # Dibujar título de la imagen
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(1*inch, y_position + img_area_height - 20, section_label)
                    
                    # Dibujar imagen centrada horizontalmente
                    x_position = (width - dw) / 2
                    buf.seek(0)
                    image = ImageReader(buf)
                    image_top = y_position + img_area_height - 40
                    c.drawImage(image, x_position, image_top - dh, 
                                width=dw, height=dh, preserveAspectRatio=True)
                    
                    # Dibujar nota debajo de la imagen (8px ≈ 6 puntos)
                    nota = im.get('note', '')
                    if nota:
                        c.setFont('Helvetica', 10)
                        nota_y = image_top - dh - 6  # 6 puntos debajo de la imagen
                        c.drawString(1*inch, nota_y, nota)
                    
            except Exception as e:
                c.setFont('Helvetica', 10)
                error_y = height - 1.5*inch - img_area_height if i % 2 == 0 else page_center - 0.5*inch - img_area_height
                c.drawString(1*inch, error_y + img_area_height - 20, f"Error al cargar imagen {i+1}: {str(e)}")

    c.save()
        # Nombre del archivo con el nombre científico
    filename = f"guia_especie_{scientific_name.replace(' ', '_')}.pdf"
    buffer.seek(0)
    return buffer, filename

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