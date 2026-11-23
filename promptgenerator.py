import os
import re
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
os.makedirs(DATA_DIR, exist_ok=True)


# Función cacheada para parsear archivos Markdown estructurados con categorías (###)
@st.cache_data
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


# Cargar datos estructurados de los archivos Markdown[cite: 2]
cameras_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "cameras.md"))[cite: 2]
photographers_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "photographers.md")
)[cite: 2]
framing_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "framing.md"))[cite: 2]
directors_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "directors.md")
)[cite: 2]
lights_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "lights.md"))
mj_style_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "midjourneystyle.md")
)


# Selector en Cascada con opción vacía por defecto[cite: 2]
def cascaded_selector(label, data_dict, key_prefix):[cite: 2]
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


# Inicializar el estado de sesión para el prompt generado[cite: 2]
if "prompt_generado" not in st.session_state:[cite: 2]
  st.session_state["prompt_generado"] = (
      "Haz clic en el botón de generar para ensamblar y traducir tu prompt."
  )


# --- INTERFAZ PRINCIPAL ---[cite: 2]
st.title("🎨 Generador de Prompts con Traducción y Filtro Dinámico")[cite: 2]
st.markdown(
    "Selecciona tus parámetros, escribe tu idea en español y pulsa el botón"
    " inferior para traducir y ensamblar el prompt final."
)[cite: 2]

col1, col2 = st.columns([1, 1], gap="large")[cite: 2]

with col1:[cite: 2]
  st.subheader("🛠️ Configuración de Escena")[cite: 2]

  subject_input = st.text_area(
      "Sujeto / Descripción principal (en español o inglés):",
      "Un ejército de marines espaciales de color azul entrando en una ciudad"
      " destruida",
      height=100,
  )[cite: 2]

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
      "Formato (Aspect Ratio):", ["--ar 16:9", "--ar 4:5", "--ar 1:1", "--ar 9:16"]
  )[cite: 2]

  st.write("")[cite: 2]
  btn_generar = st.button(
      "🚀 Generar y Traducir Prompt al Inglés", type="primary"
  )[cite: 2]


# Función auxiliar para extraer el nombre o término puro omitiendo descripciones (—) o traducciones con barra (/)[cite: 2]
def extraer_nombre_o_ingles(texto):[cite: 2]
  if not texto or texto == "-- Seleccionar --":[cite: 2]
    return ""[cite: 2]
  if "—" in texto:[cite: 2]
    texto = texto.split("—")[0].strip()[cite: 2]
  if "/" in texto:[cite: 2]
    texto = texto.split("/")[-1].strip()[cite: 2]
  return texto[cite: 2]


# Función cacheada para traducir texto general al inglés usando MyMemoryTranslator[cite: 2]
@st.cache_data
def traducir_a_ingles(texto):[cite: 2]
  if not texto or texto == "-- Seleccionar --":[cite: 2]
    return ""[cite: 2]
  try:[cite: 2]
    traducido = MyMemoryTranslator(source="es-ES", target="en-US").translate(
        texto
    )[cite: 2]
    return traducido if traducido else texto[cite: 2]
  except Exception:[cite: 2]
    return texto[cite: 2]


# SI SE PULSA EL BOTÓN DE GENERAR[cite: 2]
if btn_generar:[cite: 2]
  with st.spinner("Traduciendo selecciones y ensamblando prompt..."):[cite: 2]
    # 1. Traducir el sujeto principal introducido por el usuario[cite: 2]
    subject_clean = (
        subject_input.strip() if subject_input != "-- Seleccionar --" else ""
    )[cite: 2]
    subject_translated = (
        traducir_a_ingles(subject_clean) if subject_clean else ""
    )[cite: 2]

    # 2. Extraer nombres limpios de los desplegables comunes[cite: 2]
    light_clean = extraer_nombre_o_ingles(selected_light)
    if light_clean and "/" not in selected_light:
      light_clean = traducir_a_ingles(light_clean)

    framing_clean = extraer_nombre_o_ingles(selected_framing)[cite: 2]
    if framing_clean and "/" not in selected_framing:[cite: 2]
      framing_clean = traducir_a_ingles(framing_clean)[cite: 2]

    prompt_parts = [][cite: 2]

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
      if mj_clean:
        prompt_parts.append(f"in the style of {mj_clean}")

      prompt_parts.extend([aspect_ratio, "--v 6.0"])
    else:
      camera_clean = extraer_nombre_o_ingles(selected_camera)[cite: 2]
      photographer_clean = extraer_nombre_o_ingles(selected_photographer)[cite: 2]
      director_clean = extraer_nombre_o_ingles(selected_director)[cite: 2]
      render_clean = (
          render_engine if render_engine != "-- Seleccionar --" else ""
      )[cite: 2]

      if framing_clean and subject_translated:[cite: 2]
        prompt_parts.append(
            f"{framing_clean.lower()} of {subject_translated.lower()}"
        )[cite: 2]
      elif subject_translated:[cite: 2]
        prompt_parts.append(subject_translated.lower())[cite: 2]
      elif framing_clean:[cite: 2]
        prompt_parts.append(framing_clean.lower())[cite: 2]

      if chk_pro_photo:[cite: 2]
        prompt_parts.append(
            "professional commercial photography, award-winning composition"
        )[cite: 2]
      if chk_concept_art:[cite: 2]
        prompt_parts.append(
            "masterpiece concept art, intricate digital painting design"
        )[cite: 2]

      if director_clean:[cite: 2]
        prompt_parts.append(
            f"shot in the moody cinematic style of {director_clean}"
        )[cite: 2]
      if camera_clean:[cite: 2]
        prompt_parts.append(f"captured on {camera_clean}")[cite: 2]
      if render_clean:[cite: 2]
        prompt_parts.append(f"physically-based render with {render_clean}")[cite: 2]

      prompt_parts.append(
          "volumetric shadow, hyper-detailed surface roughness, authentic"
          " textures"
      )[cite: 2]

      if light_clean:
        prompt_parts.append(f"{light_clean.lower()} lighting")

      if photographer_clean:[cite: 2]
        prompt_parts.append(f"in the iconic style of {photographer_clean}")[cite: 2]

      prompt_parts.extend([
          aspect_ratio,
          "--v 6.0 --style raw",
          "--no text, typography, watermark, illustration, painting",
      ])[cite: 2]

    # Filtrar entradas vacías y unir con comas[cite: 2]
    final_result = ", ".join([p for p in prompt_parts if p])[cite: 2]
    st.session_state["prompt_generado"] = final_result[cite: 2]
    st.success("¡Prompt generado y traducido con éxito!")[cite: 2]


with col2:[cite: 2]
  st.subheader("⚡ Prompt Ensamblado (Midjourney v6)")[cite: 2]

  final_prompt = st.session_state["prompt_generado"][cite: 2]

  st.text_area(
      label="Prompt Completo (Listo para copiar):",
      value=final_prompt,
      height=420,
  )[cite: 2]

  # Botón de copiado con JavaScript nativo[cite: 2]
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
    """[cite: 2]
  components.html(copy_code, height=65)[cite: 2]

  st.divider()[cite: 2]
  st.markdown("### 📊 Estado de los Datos Cargados")[cite: 2]
  st.write(
      f"✔️ **framing.md**: {len(framing_dict)} categorías |"
      f" **photographers.md**: {len(photographers_dict)} categorías |"
      f" **cameras.md**: {len(cameras_dict)} categorías |"
      f" **directors.md**: {len(directors_dict)} categorías |"
      f" **lights.md**: {len(lights_dict)} categorías |"
      f" **midjourneystyle.md**: {len(mj_style_dict)} categorías"
  )[cite: 2]