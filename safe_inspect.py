import google.generativeai as genai

output_path = "tool_inspection.txt"

with open(output_path, "w") as f:
    try:
        f.write(f"SDK Version: {genai.__version__}\n\n")
        
        # Instantiate a Tool object
        t = genai.protos.Tool()
        
        f.write("Dir of genai.protos.Tool():\n")
        f.write(str(dir(t)) + "\n\n")
        
    except Exception as e:
        f.write(f"Error: {e}\n")

print(f"Written to {output_path}")
