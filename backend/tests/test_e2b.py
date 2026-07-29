from dotenv import load_dotenv
load_dotenv()

from e2b_code_interpreter import Sandbox

sbx = Sandbox.create()

code = """
print(1+2)
"""

execution = sbx.run_code(code)

print("TYPE:")
print(type(execution))

print("ERROR:")
print(execution.error)

print("TEXT:")
print(execution.text)

print("LOGS:")
print(execution.logs)

print("STDOUT:")
print(execution.logs.stdout)

print("STDERR:")
print(execution.logs.stderr)