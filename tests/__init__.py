import os

# The suite runs in Hebrew, whatever the machine's locale is; a few tests switch to English explicitly.
os.environ["LC_ALL"] = "he_IL.UTF-8"
