from flask import Flask, request, jsonify, send_file, render_template, make_response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
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
    c.setTitle(safe_get(data, ['species', 'scientificName'], 'Registro'))

    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width/2, height-150, "Registro de Especimen")
    c.setFont('Helvetica', 18)
    c.drawCentredString(width/2, height-200, safe_get(data, ['species', 'scientificName'], 'N/A'))

    c.setFont('Helvetica', 14)
    c.drawCentredString(width/2, height-250, f"Código: {data.get('code', 'N/A')}")
    c.drawCentredString(width/2, height-280, f"Fecha de Identificación: {data.get('identDate', 'N/A')}")
    museum = data.get('museum')
    if museum:
        c.drawCentredString(width/2, height-310, f"Museo: {museum.get('name', '')} ({museum.get('acronym','')})")

    c.setFont('Helvetica', 10)
    c.drawCentredString(width/2, 50, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.showPage()

    c.setFont('Helvetica-Bold', 16)
    c.drawString(1*inch, height-1*inch, "Información del Espécimen")
    c.line(1*inch, height-1*inch-5, width-1*inch, height-1*inch-5)
    y = height - 1.2*inch
    c.setFont('Helvetica', 12)

    sexo_nombre = safe_get(data, ['sex', 'name'], 'N/A')
    actividad_nombre = safe_get(data, ['activity', 'name'], 'N/A')
    bosque_nombre = safe_get(data, ['forestType', 'name'], 'N/A')

    info = [
        f"Código: {data.get('code', 'N/A')}",
        f"Nombre Científico: {safe_get(data, ['species', 'scientificName'], 'N/A')}",
        f"Nombre Común: {safe_get(data, ['species', 'commonName'], 'N/A')}",
        f"Sexo: {sexo_nombre}",
        f"Fecha de Identificación: {data.get('identDate', 'N/A')} {data.get('identTime', '')}",
        f"Actividad: {actividad_nombre}",
        f"Tipo de Bosque: {bosque_nombre}"
    ]
    for l in info:
        c.drawString(1*inch, y, l)
        y -= 20
    y -= 20

    c.setFont('Helvetica-Bold', 14)
    c.drawString(1*inch, y, "Clasificación Taxonómica:")
    y -= 20
    cls = safe_get(data, ['species', 'genus', 'family', 'order', 'class'], {})
    clase_nombre = cls.get('name', 'N/A')
    orden_nombre = safe_get(data, ['species', 'genus', 'family', 'order', 'name'], 'N/A')
    familia_nombre = safe_get(data, ['species', 'genus', 'family', 'name'], 'N/A')
    genero_nombre = safe_get(data, ['species', 'genus', 'name'], 'N/A')

    tax = [
        f"Clase: {clase_nombre}",
        f"Orden: {orden_nombre}",
        f"Familia: {familia_nombre}",
        f"Género: {genero_nombre}"
    ]
    for l in tax:
        c.drawString(1.2*inch, y, l)
        y -= 20
    y -= 20

    c.setFont('Helvetica-Bold', 14)
    c.drawString(1*inch, y, "Ubicación Geográfica:")
    y -= 20
    ev = safe_get(data, ['ocurrence', 'event'], {})
    loc = ev.get('locality', {})
    dist = loc.get('district', {})
    prov = dist.get('province', {})
    dept = prov.get('department', {})
    country = dept.get('country', {})

    locs = [
        f"Localidad: {loc.get('name', 'N/A')}",
        f"Distrito: {dist.get('name', 'N/A')}",
        f"Provincia: {prov.get('name', 'N/A')}",
        f"Departamento: {dept.get('name', 'N/A')}",
        f"País: {country.get('name', 'N/A')}",
        f"Coordenadas: Lat {ev.get('latitude', 'N/A')}, Long {ev.get('longitude', 'N/A')}"
    ]
    for l in locs:
        c.drawString(1.2*inch, y, l)
        y -= 20
    y -= 20

    identifiers = data.get('identifiers')
    if identifiers:
        c.setFont('Helvetica-Bold', 14)
        c.drawString(1*inch, y, "Identificadores:")
        y -= 20
        c.setFont('Helvetica', 12)
        for idf in identifiers:
            p = idf.get('person', {})
            line = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip()
            if p.get('email'):
                line += f" | Email: {p['email']}"
            c.drawString(1.2*inch, y, line)
            y -= 20

    imgs = safe_get(data, ['files', 'images'], [])
    if imgs:
        c.showPage()
        y = height - 1*inch
        c.setFont('Helvetica-Bold', 16)
        c.drawString(1*inch, y, "Imágenes del Especimen")
        c.line(1*inch, y-5, width-1*inch, y-5)
        y -= 30
        for im in imgs:
            try:
                r = requests.get(im['name'], timeout=10)
                r.raise_for_status()
                buf = BytesIO(r.content)
                with PILImage.open(buf) as img:
                    iw, ih = img.size
                    ar = iw/ih
                    dw = min(5*inch, iw)
                    dh = dw/ar
                    if y - dh - 50 < 0.5*inch:
                        c.showPage()
                        y = height - 1*inch
                        c.setFont('Helvetica-Bold', 16)
                        c.drawString(1*inch, y, "Imágenes del Especimen (cont.)")
                        y -= 30
                    c.setFont('Helvetica-Bold', 12)
                    c.drawString(1*inch, y, f"Imagen {im.get('order', '')}")
                    y -= 15
                    c.setFont('Helvetica', 10)
                    meta = f"Formato: {im.get('format','')}"
                    if im.get('size'): meta += f" | Tamaño: {im['size']} bytes"
                    if im.get('note'): meta += f" | Nota: {im['note']}"
                    c.drawString(1*inch, y, meta)
                    y -= 15
                    buf.seek(0)
                    image = ImageReader(buf)
                    c.drawImage(image, (width-dw)/2, y-dh, width=dw, height=dh, preserveAspectRatio=True)
                    y -= dh + 20
            except Exception as e:
                c.setFont('Helvetica', 10)
                c.drawString(1*inch, y, f"Error al cargar imagen: {e}")
                y -= 20

    c.save()
    buffer.seek(0)
    return buffer

@app.route('/generate-pdf-from-data', methods=['POST'])
def generate_pdf_from_data():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No se recibió contenido JSON"}), 400
        pdf = create_amphibian_pdf(data)
        response = make_response(pdf.read())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'inline; filename=registro.pdf')
        return response
    except Exception as e:
        return jsonify({"error": f"Error al generar PDF: {e}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)