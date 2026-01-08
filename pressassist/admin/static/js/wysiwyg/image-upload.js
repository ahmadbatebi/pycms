/**
 * CKEditor 5 Image Upload Adapter for ChelCheleh
 * Handles image uploads via the admin API
 */

/**
 * Custom upload adapter for CKEditor 5
 */
class ChelChelehUploadAdapter {
    constructor(loader) {
        this.loader = loader;
        this.csrfToken = window.CHELCHELEH_CSRF_TOKEN || '';
    }

    /**
     * Upload the file to the server
     * @returns {Promise} - Resolves with the uploaded file URL
     */
    upload() {
        return this.loader.file.then(file => {
            return new Promise((resolve, reject) => {
                const formData = new FormData();
                formData.append('file', file);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/admin/api/uploads', true);

                // Set CSRF token header
                if (this.csrfToken) {
                    xhr.setRequestHeader('X-CSRF-Token', this.csrfToken);
                }

                // Set credentials for session cookie
                xhr.withCredentials = true;

                // Handle upload progress
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable) {
                        this.loader.uploadTotal = event.total;
                        this.loader.uploaded = event.loaded;
                    }
                };

                // Handle response
                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            if (response.url) {
                                resolve({
                                    default: response.url
                                });
                            } else if (response.uuid) {
                                // Construct URL from UUID
                                resolve({
                                    default: `/uploads/${response.uuid}`
                                });
                            } else {
                                reject('آپلود موفق بود اما URL دریافت نشد');
                            }
                        } catch (e) {
                            reject('پاسخ نامعتبر از سرور');
                        }
                    } else {
                        let errorMessage = 'خطا در آپلود فایل';
                        try {
                            const response = JSON.parse(xhr.responseText);
                            errorMessage = response.detail || response.error || errorMessage;
                        } catch (e) {
                            errorMessage = xhr.statusText || errorMessage;
                        }
                        reject(errorMessage);
                    }
                };

                // Handle network errors
                xhr.onerror = () => {
                    reject('خطای شبکه در آپلود فایل');
                };

                // Handle abort
                xhr.onabort = () => {
                    reject('آپلود لغو شد');
                };

                // Store xhr for potential abort
                this.xhr = xhr;

                // Send the request
                xhr.send(formData);
            });
        });
    }

    /**
     * Abort the upload
     */
    abort() {
        if (this.xhr) {
            this.xhr.abort();
        }
    }
}

/**
 * CKEditor 5 plugin to register the upload adapter
 * @param {Object} editor - CKEditor instance
 */
function ChelChelehUploadAdapterPlugin(editor) {
    editor.plugins.get('FileRepository').createUploadAdapter = (loader) => {
        return new ChelChelehUploadAdapter(loader);
    };
}

// Export for WYSIWYG integrations
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChelChelehUploadAdapter, ChelChelehUploadAdapterPlugin };
}
