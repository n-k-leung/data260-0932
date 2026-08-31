# Run instructions for Homework 1

# Requirements
- Docker installation
- Olama installation
- Python 3.11 or 3.12

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

## Running Vulnerability Form on Docker
1. Open Docker
2. Change directory to be 
3. Run the following commands to build and run the docker image

docker build -t my-web-app .    
docker run -d -p 8032:80 --name my-web-app-container my-web-app

4. On docker you should see my-web-app and clicking on the link directs you to (http://localhost:8032). You may manually type this into your browser.

5. To view the console on this site, you can click F12 and click the Console tab. This updates when you submit to the form.

## AWS ECS