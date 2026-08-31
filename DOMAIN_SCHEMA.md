# Vulneability Form
| Field | Type | Requried | Description |
|-------|------|----------|-------------|
|'id' | string | not an input, generated with a Counter | generated with a Counter that keeps track of number of submissions |
|'packageName' | text (auto focused, primary field) | yes | Full Open-Source Package Name (e.g Python npx module) |
|'version' | text (secondary field) | yes | Version Number of the Package (e.g. 1.0.1) |
|'email' | text (auto focused, primary field) | yes | an email of the user who submit the report like last.first@gmail.com |
|'problem' | text (long input field) | yes | Describe the vulnerability, the risk it causes for the system, and/or if the open-source package version is EOL (Must be at least 25 characters long) |
|'vulSeverity' | category (dropdown) | yes | severity level of the vulnerability threat |
|'agreeTerms' | boolean (checkbox) | yes | I agree with the terms and conditions agreement |
|'timestamp' | text (auto focused, primary field) | yes | time that the form was sumbitted |

# Severity Level
| Value | Meaning |
|-------|---------|
|'Critical' | the open source pacakge must be addressed within 24hrs to ensure that the package doesnt accidently cause data leakage |
|'High' | the vulnerability will do some damage or affect the code or work that uses the open source package at this very moment and should be fixed within 2-3 days |
|'Medium' | might impact code or work that uses the open source package |
|'Low' | minor issue, not a priority fix |
