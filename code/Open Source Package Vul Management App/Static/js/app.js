// Base API URL
const API_URL = '/api/packages';

// Load packages when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadPackages();
});

function setState(state){
    const loading=document.getElementById('loadingState');
    const empty=document.getElementById('emptyState');
    const error=document.getElementById('errorState');

    loading.classList.add('hidden');
    empty.classList.add('hidden');
    error.classList.add('hidden');
    if(state==='loading')
        loading.classList.remove('hidden')
    if(state==='empty')
        empty.classList.remove('hidden')
    if(state==='error')
        error.classList.remove('hidden')
}

// Fetch and display all packages
async function loadPackages() {
    await new Promise(r => setTimeout(r, 2000));
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error('Failed to fetch packages');
        }

        const packages = await response.json();
        displayPackages(packages);
        if(packages.length ==0)
            setState('empty');
        else
            setState(null)
    } catch (error) {
        console.error('Error loading packages:', error);
        alert('Failed to load packages');
    }
}

// Display packages in the table
function displayPackages(packages) {
    const tbody = document.getElementById('packageTableBody');
    tbody.innerHTML = '';

    packages.forEach(package => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${package.id}</td>
            <td>${package.package_name}</td>
            <td>${package.severity}</td>
        `;
        tbody.appendChild(row);
    });
}
//search package by package name
async function searchPackage() {
    const searchInput = document.getElementById('searchInput');
    const package_name = searchInput.value.trim();
    if(!package_name){
        await loadPackages();
        alert('Refreshing package list');
        return;
    }
    try{
        const response = await fetch(`${API_URL}/search/${encodeURIComponent(package_name)}`);
        if(!response.ok){
            const error = await response.json();
            throw new Error(error.detail || 'Failed to search package');
        }
        const packages = await response.json();
        console.log('Search results:', packages)
        displayPackages(packages)
    } catch (error) {
        console.error('Error searching package:', error);
        alert('Failed to searching package: ' + error.message);
    }
}

// Create a new package
async function createPackage() {
    const nameInput = document.getElementById('createName');
    const severityInput = document.getElementById('createSeverity');
    const package_name = nameInput.value.trim();
    const severity = severityInput.value.trim();

    if (!package_name || !severity) {
        alert('Please enter all package vulnerability information');
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ package_name: package_name, severity:severity })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create package');
        }

        const newPackage = await response.json();
        console.log('Created package:', newPackage);

        // Clear input and reload packages
        nameInput.value = '';
        severityInput.value='';
        await loadPackages();
        alert(`Package "${newPackage.package_name}" created successfully!`);
    } catch (error) {
        console.error('Error creating package:', error);
        alert('Failed to create package: ' + error.message);
    }
}

// Update an existing package
async function updatePackage() {
    const idInput = document.getElementById('updateId');
    const nameInput = document.getElementById('updatePackageName');
    const severityInput = document.getElementById('updateSeverity');
    const id = parseInt(idInput.value);
    const package_name = nameInput.value.trim();
    const severity = severityInput.value.trim();

    if (!id || !package_name) {
        alert('Please enter package ID, package name, and severity');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ package_name: package_name, severity:severity })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update package');
        }

        const updatedPackage = await response.json();
        console.log('Updated package:', updatedPackage);

        // Clear inputs and reload packages
        idInput.value = '';
        nameInput.value = '';
        severityInput.value = '';
        await loadPackages();
        alert(`Package ID ${id} updated successfully!`);
    } catch (error) {
        console.error('Error updating package:', error);
        alert('Failed to update package: ' + error.message);
    }
}

// Delete a package
async function deletePackage() {
    const idInput = document.getElementById('deleteId');
    const id = parseInt(idInput.value);

    if (!id) {
        alert('Please enter a Package ID');
        return;
    }

    if (!confirm(`Are you sure you want to delete package ID ${id}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete package');
        }

        console.log(`Deleted package ID ${id}`);

        // Clear input and reload packages
        idInput.value = '';
        await loadPackages();
        alert(`Package ID ${id} deleted successfully!`);
    } catch (error) {
        console.error('Error deleting package:', error);
        alert('Failed to delete package: ' + error.message);
    }
}

// Delete a package with highest ID
async function deleteHighestPackage() {
    try {
        //load all books by fetching
        const response = await fetch(`${API_URL}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete package');
        }
        //verify if there are packages first before find highest id and delete
        const check = await response.json()
        
        if (check.length ==0){
            alert('No packages found to delete')
            return
        }

        //find package with highest id 
        let maxID = check[0].id;
        for (let i=1;i<check.length;i++) {
            if (check[i].id>maxID)
                maxID=check[i].id
        }

        if (!confirm(`Are you sure you want to delete package ID ${maxID}?`)) {
            return;
        }

        const delresponse = await fetch(`${API_URL}/${maxID}`, {
            method: 'DELETE'
        });

        if (!delresponse.ok) {
            const error = await delresponse.json();
            throw new Error(error.detail || 'Failed to delete package');
        }

        console.log(`Deleted package ID ${maxID}`);

        await loadPackages();
        alert(`Package ID ${maxID} deleted successfully!`);
    } catch (error) {
        console.error('Error deleting package:', error);
        alert('Failed to delete package: ' + error.message);
    }
}
