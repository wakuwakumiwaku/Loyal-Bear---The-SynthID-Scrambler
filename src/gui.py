import os
import tempfile
import gradio as gr

from src.pipeline import load_pipeline, run_img2img
from src.metadata import strip_metadata


pipe = None
model_path_default = "models/epicrealismXL_pureFix.safetensors"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

DENOISE_OPTIONS = {"Light": 0.05, "Strong": 0.1}


def load_model_on_startup():
    global pipe
    pipe = load_pipeline(model_path_default)
    return pipe is not None


def on_generate(image, prompt, denoise_mode):
    if pipe is None:
        return None, "Model not loaded. Restart the app."
    if image is None:
        return None, "Please provide an input image."

    denoise = DENOISE_OPTIONS.get(denoise_mode, 0.05)
    result = run_img2img(
        pipe,
        image=image,
        prompt=prompt,
        denoise=denoise,
        steps=5,
        cfg=6.6,
        seed=-1,
    )
    result = strip_metadata(result)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Reserve a unique filename atomically; multiple results may finish in the
    # same second, and an existing successful output must never be overwritten.
    fd, out_path = tempfile.mkstemp(prefix="output_", suffix=".png", dir=OUTPUT_DIR)
    os.close(fd)
    try:
        result.save(out_path)
    except BaseException:
        os.unlink(out_path)
        raise
    print(f"Saved: {out_path}")

    return result, f"Saved to outputs/{os.path.basename(out_path)}"


THEME = gr.themes.Base(
    primary_hue="violet",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_950",
    body_text_color="*neutral_100",
    block_background_fill="*neutral_900",
    block_label_background_fill="*neutral_900",
    block_title_background_fill="*neutral_900",
    block_label_text_color="*neutral_100",
    input_background_fill="*neutral_800",
    input_border_color="*neutral_700",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_500",
)

CSS = """
    .denoise-radio label, .denoise-radio span {
        color: #ffffff !important;
        background: transparent !important;
    }
    .denoise-radio input[type="radio"] {
        accent-color: #a78bfa !important;
    }
"""


def build_ui():
    with gr.Blocks(title="Loyal Bear – The SynthID Scrambler") as demo:
        gr.Markdown("# Loyal Bear – The SynthID Scrambler")

        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(label="Input Image", type="pil", height=400)
                prompt = gr.Textbox(label="Describe the image", lines=3)
                denoise_mode = gr.Radio(
                    label="Scrubber Strength (may affect image quality)",
                    choices=["Light", "Strong"],
                    value="Light",
                    elem_classes="denoise-radio",
                )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                output_image = gr.Image(label="Output", type="pil", height=400)
                gen_status = gr.Textbox(label="Status", interactive=False)

        generate_btn.click(
            fn=on_generate,
            inputs=[input_image, prompt, denoise_mode],
            outputs=[output_image, gen_status],
        )

    return demo
