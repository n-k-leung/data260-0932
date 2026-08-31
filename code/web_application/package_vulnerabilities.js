"use strict";
// arrow function
const validateForm= () => {
    const packageName = document.getElementById("package_name").value.trim();
    const version = document.getElementById("version_num").value.trim();
    const email = document.getElementById("email_name").value.trim();
    const problem = document.getElementById("problem_note").value.trim();
    const vulSeverity = document.getElementById("severity_level").value;
    const agreed = document.getElementById("agreeTerms").checked;

    if(!packageName || !version || !email || !problem || !vulSeverity){
        alert("All fields are required!");
        return false;
    }
    if(problem.length<=25){
        alert("Vulnerbility description must be more than 25 characters long")
        return false;
    }
    if(!agreed){
        alert("Please agree with the terms and condition before submitting")
        return false;
    }
    return true;
};

// closures
const vulCounter = (() => {
    let count = 0;
    return () => ++count;
})();

//promises and async/wait

const savevulToServer = (vulData) => {
    return new Promise((resolve, reject) => {
        console.log("Saving vul to server");
        setTimeout(() => {
            resolve(`vul from "${vulData.packageName}" saved successfully!`);
        }, 2000);
    });
};

//event listeners
document.getElementById("vulForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    //form validation
    if(!validateForm()) return;
    // collecting form data
    const packageName = document.getElementById("package_name").value;
    const version = document.getElementById("version_num").value;
    const email = document.getElementById("email_name").value;
    const problem = document.getElementById("problem_note").value;
    const vulSeverity = document.getElementById("severity_level").value;

    

    const vulData ={packageName, version, email, problem, vulSeverity, timestamp: new Date().toISOString()};

    //json operations
    const jsonvulData = JSON.stringify(vulData);
    console.log("Package Vulnerabilities Data (String):", jsonvulData);
    const parsedvulData = JSON.parse(jsonvulData);
    console.log("Package Vulnerabilities Data (JSON):", parsedvulData);

    //destructuring
    const { packageName: package_name, version: version_num, email: email_name, problem: problem_note, vulSeverity: severity_level} = parsedvulData;
    console.log("Package Name:", package_name);
    console.log("Version Number:", version_num);
    console.log("Email:", email_name);
    console.log("Vulnerability Problem Explaination:", problem_note);
    console.log("Vulnerable Severity Level:", severity_level);

    //spead operator and closures
    const currentCount = vulCounter();
    const updatedVul = { ...parsedvulData, id: `vul-${currentCount}`};
    console.log("Vul Counter: ", currentCount);
    console.log("Updated Vuls: ", updatedVul)

    //promise in action
    try{
        const serverResponse = await savevulToServer(updatedVul);
        console.log(serverResponse);
        addVulToUI(updatedVul);
        alert("Vul submitted successfully!");
    } catch(error) {
        console.error(error);
        alert(error);
    }
    document.getElementById("vulForm").reset();
});

//helper func for ui
const addVulToUI = (vulData) => {
    const {packageName, version,email,problem,vulSeverity,id} = vulData;
    const listItem = document.createElement("li");
    listItem.setAttribute("id",id);
    listItem.textContent= `Package: ${packageName} | Version: ${version} | email: ${email} | Problem: ${problem} | Severity: ${vulSeverity}`;
    const deleteButton = document.createElement("button")
    deleteButton.textContent = "Delete"
    deleteButton.onclick = handleDelete.bind(null,id);
    listItem.appendChild(deleteButton);
    document.getElementById("vulList").appendChild(listItem);
};

const handleDelete = function(id){
    const vulElement = document.getElementById(id);
    console.log(`Delete vul: ${id}`);
    vulElement.remove();
};

