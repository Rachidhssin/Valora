import re
import os
import subprocess

# Define input and output
markdown_file = r"C:\Users\MSI\.gemini\antigravity\brain\af2a4dde-3f62-4721-90f3-1db938f0f205\architecture_diagrams.md"
output_dir = r"C:\Users\MSI\Desktop\cuda_work\Valora\docs\diagrams"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Read the markdown file
with open(markdown_file, "r", encoding="utf-8") as f:
    content = f.read()

# Regex to find mermaid blocks and their titles
pattern = r"##\s+\d+\.\s+(.*?)\n+```mermaid\n(.*?)```"
matches = re.findall(pattern, content, re.DOTALL)

print(f"Found {len(matches)} diagrams.")
print(f"Generating images in: {output_dir}")

for i, (title, mermaid_code) in enumerate(matches, 1):
    # Clean title for filename
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_").strip()
    filename = f"{i}_{safe_title}.png"
    temp_mmd = os.path.join(output_dir, f"temp_{i}.mmd")
    output_png = os.path.join(output_dir, filename)
    
    # Save mermaid code to temp file
    with open(temp_mmd, "w", encoding="utf-8") as f:
        f.write(mermaid_code.strip())
    
    # Run mmdc command
    cmd = f'mmdc -i "{temp_mmd}" -o "{output_png}" -t dark -b transparent'
    try:
        print(f"Generating {filename}...")
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Generated: {filename}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate {filename}: {e}")
    finally:
        # Cleanup temp file
        if os.path.exists(temp_mmd):
            os.remove(temp_mmd)

print("\n🎉 All diagrams generated successfully!")
