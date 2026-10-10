#!/bin/bash
# Downloads the local AI model and runtime (kept out of git because of size).
set -e
cd "$(dirname "$0")"
M=models/Xenova/bert-base-NER
mkdir -p $M/onnx lib
for f in config.json special_tokens_map.json tokenizer.json tokenizer_config.json vocab.txt onnx/model_quantized.onnx; do
  [ -f "$M/$f" ] || curl -sL -o "$M/$f" "https://huggingface.co/Xenova/bert-base-NER/resolve/main/$f"
done
[ -f lib/ort-wasm-simd-threaded.jsep.wasm ] || curl -sL -o lib/ort-wasm-simd-threaded.jsep.wasm https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.5.1/dist/ort-wasm-simd-threaded.jsep.wasm
echo "Model ready."
