from openai import OpenAI
import subprocess as sp
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

'''ant_to_maven_prompt_step1 = """
You are an expert in converting Ant build files to Maven build files.
Your task is to read the provided Ant build file end to end and generate the Entire corresponding Maven build file. Ensure it covers all the dependencies, plugins,and other necessary configurations.
Generate the following Maven pom.xml file without adding any surrounding triple quotes or other formatting.
Ant build file content:
{content}
"""

ant_to_maven_prompt_step2 = """
Below is the initial Maven build file generated from the Ant build file. Enhance the following Maven pom.xml file without adding any surrounding triple quotes or other formatting.
Add the following dependencies into the Maven build file:
{dependencies}
Initial Maven build file:
{maven_content}
Output: Only directly executable Maven pom.xml file which I can automate for my next coding step.
"""'''


ant_to_maven_prompt_step1 = """
You are an expert in converting Ant build files to Maven build files.
Your task is to read the provided Ant build file end to end and generate the Entire corresponding Maven build file. Ensure it covers all the dependencies, plugins,and other necessary configurations.
Generate the following Maven pom.xml file without adding any surrounding triple quotes or other formatting.
Ant build file content:
{content}
"""

ant_to_maven_prompt_step2 = """
Below is the initial Maven `pom.xml` file migrated from an Ant build file.

**Your Task**:
- Add the provided dependencies to the `<dependencies>` section of the `pom.xml`.
- **Do not remove or modify any existing code** in the initial `pom.xml`.
- Ensure the new dependencies are correctly formatted and integrate seamlessly.

**Dependencies to Add**:
{dependencies}

**Initial Maven `pom.xml` File**:
{maven_content}

**Output**:
Provide the complete, updated `pom.xml` file with the new dependencies added. Do not include any additional text or explanations.
"""

def call_gpt(prompt):
    client = OpenAI(api_key="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")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/check-pom', methods=['GET'])
def check_pom():
    pom_exists = os.path.exists(r'D:\MavenDemo\ShippingCompany\pom.xml')
    return jsonify(pom_exists=pom_exists)

@app.route('/convert', methods=['POST'])
def convert():
    print("Received POST request at /convert")
    data = request.json
    print("Request data:", data)
    file_path = data.get('filePath')
    library_folder_path = data.get('libraryFolderPath')
    dependency_version = data.get('dependencyVersion')
    output_file_path = data.get('outputFilePath')

    print("Before Try:")

    try:
        # List all files in the specified folder
        file_names = os.listdir(library_folder_path)
        
        # Print the list of file names
        print("Files in the folder:")
        print(file_names)

        returned_text = echo_text(dependency_version)
        print("Returned text:", returned_text)

        combined_output = file_names + [("The following are the necessary versions Dependencies to include in the code that is being generated", dependency_version)]
        print("Combined output:", combined_output)

        # Open the build.xml file in read mode
        with open(file_path, 'r') as file:
            # Read the content of the file
            content = file.read()
            print("File content read successfully.")
            send_to_gpt(content, combined_output, output_file_path)
            return "You can now run your Project using Maven"
        
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return jsonify({"error": f"The file at {file_path} was not found."}), 404
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

def echo_text(text):
    """
    This function takes text as input and returns the same text as output.
    """
    return text

def execute(cmd, cwd=None):
    popen = sp.Popen(cmd, stdout=sp.PIPE, universal_newlines=True, shell=True, cwd=cwd)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise sp.CalledProcessError(return_code, cmd)

def make_changes(output_file_path):
    with open(output_file_path, 'r') as file:
        # Read the content of the file
        to_be_changed_content = file.read()
    client = OpenAI(api_key="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")
    changed_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an Assistant specialized in making an error free Maven Code. Your task is to read the provided Maven build file and generate the corresponding Executable Maven build file. Focus on generating only the necessary and executable Maven code. Do not use triple quotes at the beginning or end of the generated Maven code."},
            {"role": "user", "content": f"Make changes to the code that is necessary only for execution, based on the following Maven build file: {to_be_changed_content}"},
            
        ]
    )
    
    response_content = changed_response.choices[0].message.content.strip()
    print("GPT-3.5 Response:\n")
    print(response_content)

    with open(output_file_path, "w") as file:
        file.write(response_content)
    return run_maven_build(output_file_path)

def send_to_gpt(content, combined_output, output_file_path):
    try:
        prompt_step1 = ant_to_maven_prompt_step1.format(content=content)
        initial_maven_content = call_gpt(prompt_step1)
        print("Initial Maven Content:\n")
        print(initial_maven_content)

        # Step 2: Incorporate dependencies into the Maven build file
        prompt_step2 = ant_to_maven_prompt_step2.format(maven_content=initial_maven_content, dependencies=combined_output)
        final_maven_content = call_gpt(prompt_step2)
        print("Final Maven Content:\n")
        print(final_maven_content)

        with open(output_file_path, "w") as file:
            file.write(final_maven_content)
        return run_maven_build(output_file_path)

    except Exception as e:
        print(f"An error occurred while communicating with OpenAI: {e}")

def run_maven_build(output_file_path):
    pom_exists = os.path.exists(output_file_path)
    if pom_exists:
        directory_path = os.path.dirname(output_file_path)
        print(f"Running Maven build in directory: {directory_path}") 

        max_attempts = 2
        attempt = 0
        #success = False
        #message = ""

        log_file_path = os.path.join(directory_path, "maven_build_log.txt")
        with open(log_file_path, "w") as log_file:
            while attempt < max_attempts:
                try:
                    print(f"Running Maven build in directory: {directory_path}")

                    output_log = []
                    # Run 'mvn validate'
                    for output in execute("mvn validate", cwd=directory_path):
                        output_log.append(output)
                        log_file.write(output)
                        log_file.flush()
                        print(output, end="")
        
                    print("Maven validate successful.")
                    print("Log output:")
                    print("\n".join(output_log))
                
                    for output in execute("mvn clean", cwd=directory_path):
                        log_file.write(output)
                        log_file.flush()
                        print(output, end="")
        
                    # Run 'mvn install'
                    for output in execute("mvn install", cwd=directory_path):
                        log_file.write(output)
                        log_file.flush()
                        print(output, end="")
        
                    print("Maven build process completed.")
                    message = "Build successful. You can now run your Project using Maven."
                    success = True
                    break
                except sp.CalledProcessError as e:
                    print(f"Validation failed on attempt {attempt + 1}: {e}")
                    make_changes(output_file_path)
                    attempt += 1
                    if attempt == max_attempts:
                        print("Maximum attempts reached. Build failed.")
                        message = "Build failed. Please check the logs for details."
                    else:
                        message = "Conversion completed, but pom.xml does not exist"

        print(f"Final message: {message}")
        status_code = 200 if success else 500
        response = jsonify(message=message)
        response.status_code = status_code
        return response

if __name__ == '__main__':
    app.run(debug=True)