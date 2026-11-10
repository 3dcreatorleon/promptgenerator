import importlib.util
import os
import re
import subprocess
import sys


def verificar_e_instalar(paquete_pip, import_nombre=None):
  if import_nombre is None:
    import_nombre = paquete_pip
  if importlib.util.find_spec(import_nombre) is None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", paquete_pip]
    )


# Asegurar dependencias necesarias
verificar_e_instalar("streamlit")
verificar_e_instalar("deep-translator", "deep_translator")

import streamlit as st
import streamlit.components.v1 as components
from deep_translator import MyMemoryTranslator

st.set_page_config(
    page_title="Generador de Prompts con Traducción Dinámica", layout="wide"
)

# Estilo CSS para forzar el ajuste de línea en la caja del prompt
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


# Función para parsear archivos Markdown estructurados con categorías (###)
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


# Cargar datos estructurados de los archivos Markdown
cameras_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "cameras.md"))
photographers_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "photographers.md")
)
framing_dict = parse_markdown_categorized(os.path.join(DATA_DIR, "framing.md"))
directors_dict = parse_markdown_categorized(
    os.path.join(DATA_DIR, "directors.md")
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


# Inicializar el estado de sesión para el prompt generado
if "prompt_generado" not in st.session_state:
  st.session_state["prompt_generado"] = (
      "Haz clic en el botón de generar para ensamblar y traducir tu prompt."
  )


# --- INTERFAZ PRINCIPAL ---
st.title("🎨 Generador de Prompts con Traducción y Filtro Dinámico")
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
  )

  st.write("")
  btn_generar = st.button(
      "🚀 Generar y Traducir Prompt al Inglés", type="primary"
  )


# Función auxiliar para extraer el nombre/término puro limpiando descripciones y formatos bilingües
def extraer_nombre_o_ingles(texto):
  if not texto or texto == "-- Seleccionar --":
    return ""
  # Si tiene una descripción separada por guion largo (ej: "Christopher Nolan — Especialista en...")
  if "—" in texto:
    texto = texto.split("—")[0].strip()
  # Si tiene formato bilingüe de encuadre (ej: "Español / English")
  if "/" in texto:
    texto = texto.split("/")[-1].strip()
  return texto


# Función para traducir texto general al inglés usando MyMemoryTranslator
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


# SI SE PULSA EL BOTÓN DE GENERAR
if btn_generar:
  with st.spinner("Traduciendo selecciones y ensamblando prompt..."):
    # 1. Traducir el sujeto principal escrito por el usuario
    subject_clean = (
        subject_input.strip() if subject_input != "-- Seleccionar --" else ""
    )
    subject_translated = (
        traducir_a_ingles(subject_clean) if subject_clean else ""
    )

    # 2. Extraer nombres limpios de los desplegables
    framing_clean = extraer_nombre_o_ingles(selected_framing)
    camera_clean = extraer_nombre_o_ingles(selected_camera)
    photographer_clean = extraer_nombre_o_ingles(selected_photographer)
    director_clean = extraer_nombre_o_ingles(selected_director)
    render_clean = (
        render_engine if render_engine != "-- Seleccionar --" else ""
    )

    # Si el encuadre estaba en español y no contenía barra '/', se traduce
    if framing_clean and "/" not in selected_framing:
      framing_clean = traducir_a_ingles(framing_clean)

    # 3. Construcción modular del prompt en inglés
    prompt_parts = []

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
      prompt_parts.append(f"shot in the moody cinematic style of {director_clean}")
    if camera_clean:
      prompt_parts.append(f"captured on {camera_clean}")
    if render_clean:
      prompt_parts.append(f"physically-based render with {render_clean}")

    prompt_parts.append(
        "volumetric shadow, hyper-detailed surface roughness, authentic textures"
    )

    if photographer_clean:
      prompt_parts.append(f"in the iconic style of {photographer_clean}")

    prompt_parts.extend([
        aspect_ratio,
        "--v 6.0 --style raw",
        "--no text, typography, watermark, illustration, painting",
    ])

    # Filtrar elementos vacíos y unir con comas
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

  # Botón de copiado avanzado con JavaScript nativo
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
  st.markdown("### 📊 Estado de los Datos Cargados")
  st.write(
      f"✔️ **framing.md**: {len(framing_dict)} categorías |"
      f" **photographers.md**: {len(photographers_dict)} categorías |"
      f" **cameras.md**: {len(cameras_dict)} categorías |"
      f" **directors.md**: {len(directors_dict)} categorías"
  )