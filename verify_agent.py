import os
import sys
sys.path.insert(0, '.')
import ollama_agent

print(ollama_agent.run_agent('Create a source file called src/app.js with the content console.log(\"hello\"); and then validate that the file exists', workspace=os.getcwd(), max_steps=3))
