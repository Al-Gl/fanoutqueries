import google.generativeai as genai
import sys

output_path = "proto_info_direct.txt"

with open(output_path, "w", encoding="utf-8") as f:
    try:
        f.write(f"SDK Version: {genai.__version__}\n")
        
        tool_proto = genai.protos.Tool()
        f.write("Available fields in genai.protos.Tool:\n")
        # descriptor names
        fields = [field.name for field in tool_proto.DESCRIPTOR.fields]
        f.write(str(fields) + "\n")
        
    except Exception as e:
        f.write(f"Error inspecting proto: {e}\n")

print(f"Written to {output_path}")
