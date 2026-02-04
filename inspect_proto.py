import google.generativeai as genai
import pprint

print(f"SDK Version: {genai.__version__}")

try:
    tool_proto = genai.protos.Tool()
    print("Available fields in genai.protos.Tool:")
    # descriptor names
    print([f.name for f in tool_proto.DESCRIPTOR.fields])
except Exception as e:
    print(f"Error inspecting proto: {e}")
