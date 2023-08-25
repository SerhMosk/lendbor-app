import {HOST, PORT, SSL} from "./config.js";

const API_URL = `http${SSL ? 's' : ''}://${HOST}:${PORT}/`;

const request = (url, options) => {
    return fetch(`${API_URL}${url}`, options)
        .then(response => {
            if (!response.ok) {
                throw `${response.status} - ${response.statusText}`;
            }
            console.log(`${API_URL}${url}`, response);
            return response.json();
        })
    // .catch(error => console.log(error));
};

const get = (url) => request(url);

const post = (url, data) => {
    return request(url, {
        method: 'POST',
        headers: {
            'Content-type': 'application/json; charset=UTF-8'
        },
        body: JSON.stringify(data),
    });
};

const patch = (url, data) => {
    return request(url, {
        method: 'PATCH',
        headers: {
            'Content-type': 'application/json; charset=UTF-8'
        },
        body: JSON.stringify(data),
    });
};

const remove = (url) => request(url, {method: 'DELETE'});

const getFormData = (formId) => {
    const selects = document.querySelectorAll(`#${formId} select`);
    const values = Array.from(selects).reduce((acc, select) => ({...acc, [select.name]: select.value}), {});
    const inputs = document.querySelectorAll(`#${formId} input`);
    return Array.from(inputs).reduce((acc, input) => ({...acc, [input.name]: input.value}), values);
};

const xhrRequest = (method, url, formData, form, redirectUrl = null, message = null) => {
    // Create an XMLHttpRequest or fetch API request
    const xhr = new XMLHttpRequest(); // or use: fetch(url, { method: 'POST', body: formData });
    xhr.open(method, `${API_URL}${url}`, true); // Specify the URL of your Python backend
    xhr.send(formData); // Send the form data
    // Handle the response from the Python backend
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status === 200) {
                // Request successful, do something with the response
                // console.log(xhr.responseText);
                // alert("This form has been successfully submitted!");

                form.reset();

                if (redirectUrl) {
                    window.location.href = `${API_URL}${redirectUrl}`;
                }
            } else {
                // Request failed, handle the error
                // console.error(xhr);
                const serverError = document.getElementById("serverError");
                if (serverError) {
                    const errorMsg = xhr.responseText ? '<br>' + xhr.responseText : '';
                    serverError.innerHTML = xhr.status + ' - ' + xhr.statusText + errorMsg;
                }
            }
        }
    };
};

const addUserForm = document.getElementById("addUserForm");
if (addUserForm) {
    addUserForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const data = getFormData('addUserForm');
        const formData = new FormData(addUserForm); // Create a FormData object with form data
        // console.log(data);

        if (data.username === "" || data.password === "") {
            alert("Ensure you input a value in both fields!");
        } else {
            // Perform operation with form input
            xhrRequest('POST', 'users/create', formData, addUserForm, 'users');
        }
    });
}

const addRecordForm = document.getElementById("addRecordForm");
if (addRecordForm) {
    $('#last_date').datepicker();

    addRecordForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const data = getFormData('addRecordForm');
        const formData = new FormData(addRecordForm); // Create a FormData object with form data
        // console.log(data);

        if (data.type === "" || data.name === "" || data.amount === "" || data.months === "" || data.payment_amount === "" || data.payment_day === "") {
            alert("Ensure you input a value in both fields!");
        } else {
            // Perform operation with form input
            xhrRequest('POST', 'records/create', formData, addRecordForm, 'records');
        }
    });
}

const addPaymentForm = document.getElementById("addPaymentForm");
if (addPaymentForm) {
    $('#payment_date').datepicker();

    addPaymentForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const data = getFormData('addPaymentForm');
        const formData = new FormData(addPaymentForm); // Create a FormData object with form data
        // console.log(data);

        if (!data.record_id || !data.user_id || data.record_id === '0' || data.user_id === '0') {
            alert("Ensure you input a value in both fields!");
        } else {
            // Perform operation with form input
            xhrRequest('POST', 'payments/create', formData, addPaymentForm, 'payments');
        }
    });
}

const $deleteButtons = $('.btn-delete');
if ($deleteButtons.length) {
    $deleteButtons.on('click', (e) => {
        const target = e.target.classList.contains('bi-trash') ? e.target.parentNode : e.target;
        $('#confirmDelete').data('url', $(target).data('url')).data('redirect_url', $(target).data('redirect_url'));
    });

    $('#confirmDelete').on('click', '#btnDelete', (e) => {
        const $modalDiv = $(e.delegateTarget);
        const {url, redirect_url} = $modalDiv.data();
        // console.log($modalDiv.data());

        $.ajax({type: "DELETE", url}).then((res) => {
            if (res === 'OK') {
                $modalDiv.modal('hide');
                if (redirect_url) {
                    window.location.href = `${API_URL}${redirect_url}`;
                }
            }
        });
    });
}
