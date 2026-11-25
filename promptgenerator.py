import os
import re
import unicodedata
import numpy as np
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
from deep_translator import MyMemoryTranslator

st.set_page_config(
    page_title="Generador de Prompts con Traducción Dinámica", layout="wide"
)

# Estilo CSS para forzar el ajuste de línea (word-wrap) en la caja del prompt
st.markdown(
    """
    <style>
    div[data-baseweb="textarea"] textarea {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        font-family: monospace;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DATA_DIR = "./markdowns"
ARTISTS_DIR = os.path.join(DATA_DIR, "artistas")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARTISTS_DIR, exist_ok=True)


# Función cacheada para parsear archivos Markdown estructurados con categorías
@st.cache_data(ttl=60)
def parse_markdown_categorized(filepath):
  categories = {}
  current_cat = "-- Seleccionar --"
  categories[current_cat] = []

  if os.path.exists(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
      for line in f:
        line_str = line.strip()
        if line_str.startswith("###") or line_str.startswith("##"):
          current_cat = re.sub(r"^#+\s*", "", line_str).strip()
          if current_cat not in categories:
            categories[current_cat] = []
        elif line_str.startswith("-") or line_str.startswith("*"):
          item = re.sub(r"^[-*]\s+", "", line_str).strip()
          if item:
            categories[current_cat].append(item)
        elif (
            line_str
            and not line_str.startswith("#")
            and not line_str.startswith("```")
        ):
          categories[current_cat].append(line_str)

  categories = {k: v for k, v in categories.items() if v}
  if not categories:
    categories["-- Seleccionar --"] = ["-- Seleccionar --"]
  return categories


# Convierte el nombre de un artista en el nombre de archivo esperado (slug)
def slugify_artist(nombre):
  if not nombre:
    return ""
  texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
  texto = texto.lower()
  texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
  return texto


# Lee la ficha individual del artista en ./markdowns/artistas/<slug>.md si existe
@st.cache_data(ttl=60)
def cargar_ficha_artista(artist_name):
  slug = slugify_artist(artist_name)
  if not slug:
    return None, None

  filepath = os.path.join(ARTISTS_DIR, f"{slug}.md")
  if not os.path.exists(filepath):
    return None, None

  prompt_base_lines = []
  params_lines = []
  seccion_actual = None

  with open(filepath, "r", encoding="utf-8") as f:
    for line in f:
      line_str = line.strip()
      if line_str.startswith("## "):
        header_lower = line_str[3:].strip().lower()
        if "prompt base" in header_lower:
          seccion_actual = "prompt"
        elif "parámetros" in header_lower or "parametros" in header_lower:
          seccion_actual = "params"
        else:
          seccion_actual = None
      elif line_str and not line_str.startswith("#"):
        if seccion_actual == "prompt":
          prompt_base_lines.append(line_str)
        elif seccion_actual == "params":
          params_lines.append(line_str)

  prompt_base = ", ".join(prompt_base_lines).strip()
  params_extra = " ".join(params_lines).strip()
  return prompt_base, params_extra


# Cargar datos estructurados de los archivos Markdown
cameras_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "cameras.md"))
photographers_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "photographers.md")
)
framing_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "framing.md"))
directors_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "directors.md")
)
lights_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "lights.md"))
mj_style_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "midjourneystyle.md")
)


# Selector en Cascada con opción vacía por defecto
def cascaded_selector(label, data_dict, key_prefix):
  categories = ["-- Seleccionar --"] + [
      c for c in data_dict.keys() if c != "-- Seleccionar --"
  ]
  selected_cat = st.selectbox(
      f"{label} - Categoría:", categories, key=f"{key_prefix}_cat"
  )

  if selected_cat == "-- Seleccionar --":
    items_in_cat = ["-- Seleccionar --"]
  else:
    items_in_cat = ["-- Seleccionar --"] + data_dict.get(
        selected_cat, ["-- Seleccionar --"]
    )

  selected_item = st.selectbox(
      f"{label} - Nombre / Específico:", items_in_cat, key=f"{key_prefix}_item"
  )
  return selected_item


# Función auxiliar para extraer el nombre o término puro omitiendo descripciones (—) o traducciones con barra (/)
def extraer_nombre_o_ingles(texto):
  if not texto or texto == "-- Seleccionar --":
    return ""
  if "—" in texto:
    texto = texto.split("—")[0].strip()
  if "/" in texto:
    texto = texto.split("/")[-1].strip()
  return texto


# Extrae la característica tras el guion largo (—) en midjourneystyle.md como respaldo
def extraer_caracteristica_md(texto):
  if not texto or texto == "-- Seleccionar --" or "—" not in texto:
    return ""
  return texto.split("—", 1)[1].strip()


# Función cacheada para traducir texto general al inglés usando MyMemoryTranslator
@st.cache_data
def traducir_a_ingles(texto):
  if not texto or texto == "-- Seleccionar --":
    return ""
  try:
    traducido = MyMemoryTranslator(source="es-ES", target="en-US").translate(
        texto
    )
    return traducido if traducido else texto
  except Exception:
    return texto


# --- FUNCIONES PARA IDENTIFICAR ESTILO Y ARTISTA EN midjourneystyle.md (SIN API) ---
def extraer_rasgos_imagen(pil_image):
  pequena = pil_image.resize((200, 200))
  hsv = pequena.convert("HSV")
  rgb = pequena.convert("RGB")
  gray = pequena.convert("L")

  arr_hsv = np.array(hsv, dtype=np.float32)
  arr_rgb = np.array(rgb, dtype=np.float32)
  arr_gray = np.array(gray, dtype=np.float32)

  brillo = float(arr_gray.mean()) / 255.0
  contraste = float(arr_gray.std()) / 255.0
  saturacion = float(arr_hsv[:, :, 1].mean()) / 255.0
  calidez = (float(arr_rgb[:, :, 0].mean()) - float(arr_rgb[:, :, 2].mean())) / 255.0

  pistas = []
  if saturacion < 0.14:
    pistas.extend(["monochrome", "black and white", "blanco y negro", "muted"])
  elif saturacion > 0.45:
    pistas.extend(["vibrant", "neon", "saturated", "colorful", "cyberpunk", "pop"])
  else:
    pistas.extend(["cinematic", "editorial", "atmospheric"])

  if brillo < 0.32:
    pistas.extend(["dark", "night", "nocturnal", "noir", "gothic", "shadow", "chiaroscuro", "oscura"])
  elif brillo > 0.72:
    pistas.extend(["bright", "pastel", "daylight", "luminosa", "clara"])

  if calidez > 0.08:
    pistas.extend(["warm", "golden", "amber", "sunset", "ochre", "cálida"])
  elif calidez < -0.08:
    pistas.extend(["cold", "blue", "cyan", "rain", "fría"])

  if contraste > 0.25:
    pistas.extend(["contrast", "dramatic", "ink", "graphic", "contraste"])

  return set(pistas)


def identificar_estilo_y_artista(pil_image, style_dict):
  pistas = extraer_rasgos_imagen(pil_image)
  mejor_estilo = None
  mejor_artista = None
  mejor_puntos = -1

  for estilo, artistas in style_dict.items():
    if estilo == "-- Seleccionar --" or not artistas:
      continue
    estilo_puntos = sum(1 for p in pistas if p in estilo.lower())

    for entrada in artistas:
      entrada_lower = entrada.lower()
      artista_puntos = sum(1 for p in pistas if p in entrada_lower)
      total = estilo_puntos + (artista_puntos * 2)
      if total > mejor_puntos:
        mejor_puntos = total
        mejor_estilo = estilo
        mejor_artista = extraer_nombre_o_ingles(entrada) or entrada

  return mejor_estilo, mejor_artista


# Inicializar estado de sesión
if "prompt_generado" not in st.session_state:
  st.session_state["prompt_generado"] = (
      "Haz clic en el botón de generar para ensamblar y traducir tu prompt."
  )

# --- INTERFAZ PRINCIPAL ---
st.title("🎨 Generador de Prompts con Traducción y Filtro Dinámico")

tab_gen, tab_id = st.tabs(
    ["🛠️ Generador de Prompts", "🔍 Identificador de Estilo y Artista"]
)

# ==========================================
# PESTAÑA 1: GENERADOR DE PROMPTS
# ==========================================
with tab_gen:
  st.markdown(
      "Selecciona tus parámetros, escribe tu idea en español y pulsa el botón"
      " inferior para traducir y ensamblar el prompt final."
  )

  col1, col2 = st.columns([1, 1], gap="large")

  with col1:
    st.subheader("🛠️ Configuración de Escena")

    subject_input = st.text_area(
        "Sujeto / Descripción principal (en español o inglés):",
        "Un ejército de marines espaciales de color azul entrando en una ciudad"
        " destruida",
        height=100,
    )

    # Desplegables en cascada para categoría y tipo de luz desde lights.md
    selected_light = cascaded_selector("Iluminación", lights_dict, "light")

    # Check exclusivo para activar el modo Estilo Midjourney
    chk_midjourney_style = st.checkbox("Estilo Midjourney", value=False)

    chk_pro_photo = False
    chk_concept_art = False
    selected_mj_artist = "-- Seleccionar --"
    selected_camera = "-- Seleccionar --"
    selected_photographer = "-- Seleccionar --"
    selected_framing = "-- Seleccionar --"
    selected_director = "-- Seleccionar --"
    render_engine = "-- Seleccionar --"

    if chk_midjourney_style:
      # En modo Midjourney aparecen los desplegables de Estilo Midjourney y también Encuadre
      selected_mj_artist = cascaded_selector(
          "Estilo Midjourney", mj_style_dict, "mj_style"
      )
      selected_framing = cascaded_selector("Encuadre", framing_dict, "frame")
    else:
      # En el resto de los casos aparecen todas las categorías de fotografía y cine
      col_chk1, col_chk2 = st.columns(2)
      with col_chk1:
        chk_pro_photo = st.checkbox("Fotografía profesional", value=True)
      with col_chk2:
        chk_concept_art = st.checkbox("Arte conceptual", value=False)

      selected_camera = cascaded_selector("Cámara", cameras_dict, "cam")
      selected_photographer = cascaded_selector(
          "Fotógrafo", photographers_dict, "photo"
      )
      selected_framing = cascaded_selector("Encuadre", framing_dict, "frame")
      selected_director = cascaded_selector("Director", directors_dict, "dir")

      render_engine = st.selectbox(
          "Motor de Renderizado:",
          [
              "-- Seleccionar --",
              "Chaos Corona Renderer",
              "Octane Render",
              "Unreal Engine 5.4",
              "Fotografía Real (Sin motor 3D)",
          ],
      )

    aspect_ratio = st.selectbox(
        "Formato (Aspect Ratio):",
        ["--ar 16:9", "--ar 4:5", "--ar 1:1", "--ar 9:16"],
    )

    st.write("")
    btn_generar = st.button(
        "🚀 Generar y Traducir Prompt al Inglés", type="primary"
    )

  # SI SE PULSA EL BOTÓN DE GENERAR
  if btn_generar:
    with st.spinner("Traduciendo selecciones y ensamblando prompt..."):
      subject_clean = (
          subject_input.strip() if subject_input != "-- Seleccionar --" else ""
      )
      subject_translated = (
          traducir_a_ingles(subject_clean) if subject_clean else ""
      )

      light_clean = extraer_nombre_o_ingles(selected_light)
      if light_clean and "/" not in selected_light:
        light_clean = traducir_a_ingles(light_clean)

      framing_clean = extraer_nombre_o_ingles(selected_framing)
      if framing_clean and "/" not in selected_framing:
        framing_clean = traducir_a_ingles(framing_clean)

      prompt_parts = []

      if chk_midjourney_style:
        mj_clean = extraer_nombre_o_ingles(selected_mj_artist)
        if mj_clean and "/" not in selected_mj_artist:
          mj_clean = traducir_a_ingles(mj_clean)

        if framing_clean and subject_translated:
          prompt_parts.append(
              f"{framing_clean.lower()} of {subject_translated.lower()}"
          )
        elif subject_translated:
          prompt_parts.append(subject_translated.lower())
        elif framing_clean:
          prompt_parts.append(framing_clean.lower())

        if light_clean:
          prompt_parts.append(f"{light_clean.lower()} lighting")

        extra_params = ""
        if mj_clean:
          # 1. Intentar leer la ficha individual en ./markdowns/artistas/<slug>.md
          ficha_prompt, ficha_params = cargar_ficha_artista(mj_clean)
          if ficha_prompt:
            prompt_parts.append(ficha_prompt)
            prompt_parts.append(f"in the style of {mj_clean}")
            extra_params = ficha_params
          else:
            # 2. Respaldo automático usando la característica de midjourneystyle.md
            caract_es = extraer_caracteristica_md(selected_mj_artist)
            if caract_es:
              caract_en = traducir_a_ingles(caract_es)
              if caract_en:
                prompt_parts.append(caract_en.lower())
            prompt_parts.append(f"in the style of {mj_clean}")

        # Ajustar versión/modelo si la ficha recomienda --niji 6
        if "--niji" in extra_params:
          prompt_parts.extend([aspect_ratio, extra_params])
        else:
          mj_tail = f"--v 6.0 {extra_params}".strip()
          prompt_parts.extend([aspect_ratio, mj_tail])
      else:
        camera_clean = extraer_nombre_o_ingles(selected_camera)
        photographer_clean = extraer_nombre_o_ingles(selected_photographer)
        director_clean = extraer_nombre_o_ingles(selected_director)
        render_clean = (
            render_engine if render_engine != "-- Seleccionar --" else ""
        )

        if framing_clean and subject_translated:
          prompt_parts.append(
              f"{framing_clean.lower()} of {subject_translated.lower()}"
          )
        elif subject_translated:
          prompt_parts.append(subject_translated.lower())
        elif framing_clean:
          prompt_parts.append(framing_clean.lower())

        if chk_pro_photo:
          prompt_parts.append(
              "professional commercial photography, award-winning composition"
          )
        if chk_concept_art:
          prompt_parts.append(
              "masterpiece concept art, intricate digital painting design"
          )

        if director_clean:
          prompt_parts.append(
              f"shot in the moody cinematic style of {director_clean}"
          )
        if camera_clean:
          prompt_parts.append(f"captured on {camera_clean}")
        if render_clean:
          prompt_parts.append(f"physically-based render with {render_clean}")

        prompt_parts.append(
            "volumetric shadow, hyper-detailed surface roughness, authentic"
            " textures"
        )

        if light_clean:
          prompt_parts.append(f"{light_clean.lower()} lighting")

        if photographer_clean:
          prompt_parts.append(f"in the iconic style of {photographer_clean}")

        prompt_parts.extend([
            aspect_ratio,
            "--v 6.0 --style raw",
            "--no text, typography, watermark, illustration, painting",
        ])

      final_result = ", ".join([p for p in prompt_parts if p])
      st.session_state["prompt_generado"] = final_result
      st.success("¡Prompt generado y traducido con éxito!")

  with col2:
    st.subheader("⚡ Prompt Ensamblado (Midjourney v6)")

    final_prompt = st.session_state["prompt_generado"]

    st.text_area(
        label="Prompt Completo (Listo para copiar):",
        value=final_prompt,
        height=420,
    )

    copy_code = f"""
        <script>
        function copyPromptToClipboard() {{
            const textToCopy = `{final_prompt}`;
            navigator.clipboard.writeText(textToCopy).then(() => {{
                const btn = document.getElementById("copyBtn");
                btn.innerText = "¡Copiado con éxito! ✅";
                btn.style.backgroundColor = "#28a745";
                setTimeout(() => {{
                    btn.innerText = "📋 Copiar Prompt al Portapapeles";
                    btn.style.backgroundColor = "#FF4B4B";
                }}, 2000);
            }}).catch(err => {{
                console.error('Error al copiar: ', err);
            }});
        }}
        </script>
        <button id="copyBtn" onclick="copyPromptToClipboard()" style="
            width: 100%;
            background-color: #FF4B4B;
            color: white;
            border: none;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        ">
            📋 Copiar Prompt al Portapapeles
        </button>
        """
    components.html(copy_code, height=65)

    st.divider()
    fichas_artistas_count = (
        len([f for f in os.listdir(ARTISTS_DIR) if f.endswith(".md")])
        if os.path.exists(ARTISTS_DIR)
        else 0
    )
    st.markdown("### 📊 Estado de los Datos Cargados")
    st.write(
        f"✔️ **framing.md**: {len(framing_dict)} categorías |"
        f" **photographers.md**: {len(photographers_dict)} categorías |"
        f" **cameras.md**: {len(cameras_dict)} categorías |"
        f" **directors.md**: {len(directors_dict)} categorías |"
        f" **lights.md**: {len(lights_dict)} categorías |"
        f" **midjourneystyle.md**: {len(mj_style_dict)} categorías |"
        f" **Fichas individuales (`artistas/`)**: {fichas_artistas_count}"
    )

# ==========================================
# PESTAÑA 2: IDENTIFICADOR DE ESTILO Y ARTISTA
# ==========================================
with tab_id:
  st.subheader("🔍 Identificador de Estilo y Artista")

  uploaded_img = st.file_uploader(
      "Sube o pega una imagen:",
      type=["png", "jpg", "jpeg", "webp"],
      key="id_image_uploader_simple",
  )

  pil_img = None
  if uploaded_img is not None:
    pil_img = Image.open(uploaded_img).convert("RGB")
    st.image(pil_img, caption="Imagen cargada", use_container_width=True)

  if st.button("🎯 Identificar", type="primary", disabled=(pil_img is None)):
    estilo_encontrado, artista_encontrado = identificar_estilo_y_artista(
        pil_img, mj_style_dict
    )
    st.markdown(f"**Estilo:** {estilo_encontrado or 'No identificado'}")
    st.markdown(f"**Artista:** {artista_encontrado or 'No identificado'}")
