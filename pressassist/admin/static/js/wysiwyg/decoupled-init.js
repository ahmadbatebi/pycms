/* Decoupled CKEditor initialization and custom controls */
(function() {
    'use strict';

    /**
     * Clean CKEditor accessibility text from content
     * These are aria-label texts that get accidentally included when copying/pasting
     */
    function cleanEditorContent(html) {
        if (!html) return html;

        // Remove CKEditor widget labels that shouldn't be saved
        // These include accessibility labels with image alt text
        var patterns = [
            // Media widget labels (Persian)
            /ویجت رسانه\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // Image widget labels with any alt text (Persian) - matches "تصویر ALT_TEXT ابزاره تصویر. Press..."
            /تصویر\s+[^\n]*?\s*ابزاره تصویر\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // Simple image widget label (Persian)
            /ابزاره تصویر\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // English versions
            /Media widget\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            /Image widget\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            /Widget toolbar\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // Image with alt text (English) - matches "IMAGE_ALT Image widget. Press..."
            /[^\n<>]*?\s*Image widget\.\s*Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // Catch any remaining widget instructions
            /Press Enter to type after or press Shift \+ Enter to type before the widget/gi,
            // Standalone Persian labels that might remain (not inside HTML attributes)
            /(?<![">])ابزاره تصویر\.(?![<"])/gi,
            /(?<![">])ویجت رسانه\.(?![<"])/gi,
            // Standalone lines with alt text artifacts (after closing tags)
            /(?<=>)\s*\n\s*تصویر\s+\S+\s*\n\s*\n/gi,
            // Remove empty paragraphs that may be left behind
            /<p>\s*<\/p>/gi,
            /<p>&nbsp;<\/p>/gi
        ];

        var cleaned = html;
        patterns.forEach(function(pattern) {
            cleaned = cleaned.replace(pattern, '');
        });

        // Clean up multiple consecutive empty lines/spaces
        cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n');

        // Clean up trailing whitespace lines
        cleaned = cleaned.replace(/\n\s+$/g, '');

        return cleaned.trim();
    }

    /**
     * Custom upload adapter for CKEditor 5
     */
    class ChelChelehUploadAdapter {
        constructor(loader) {
            this.loader = loader;
            this.csrfToken = window.CHELCHELEH_CSRF_TOKEN || '';
        }

        upload() {
            return this.loader.file.then(file => {
                return new Promise((resolve, reject) => {
                    const formData = new FormData();
                    formData.append('file', file);

                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', '/admin/api/uploads', true);

                    if (this.csrfToken) {
                        xhr.setRequestHeader('X-CSRF-Token', this.csrfToken);
                    }
                    xhr.withCredentials = true;

                    xhr.upload.onprogress = (event) => {
                        if (event.lengthComputable) {
                            this.loader.uploadTotal = event.total;
                            this.loader.uploaded = event.loaded;
                        }
                    };

                    xhr.onload = () => {
                        if (xhr.status >= 200 && xhr.status < 300) {
                            try {
                                const response = JSON.parse(xhr.responseText);
                                if (response.url) {
                                    resolve({ default: response.url });
                                } else if (response.uuid) {
                                    resolve({ default: `/uploads/${response.uuid}` });
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

                    xhr.onerror = () => reject('خطای شبکه در آپلود فایل');
                    xhr.onabort = () => reject('آپلود لغو شد');
                    this.xhr = xhr;
                    xhr.send(formData);
                });
            });
        }

        abort() {
            if (this.xhr) {
                this.xhr.abort();
            }
        }
    }

    function UploadAdapterPlugin(editor) {
        editor.plugins.get('FileRepository').createUploadAdapter = (loader) => {
            return new ChelChelehUploadAdapter(loader);
        };
    }

    function initEditors() {
        var textareas = document.querySelectorAll(
            'textarea[name="content"], textarea#block-content, textarea#block-content-fa, textarea#block-content-en, textarea.wysiwyg-editor'
        );

        if (!textareas.length) {
            console.log('No textareas found for WYSIWYG editor');
            return;
        }

        console.log('Found', textareas.length, 'textarea(s) for WYSIWYG editor');

        textareas.forEach(function(textarea) {
            if (textarea.dataset.editorInitialized === 'true') return;

            // Create container for decoupled editor
            var wrapper = document.createElement('div');
            wrapper.className = 'ck-editor-wrapper';

            var toolbarWrapper = document.createElement('div');
            toolbarWrapper.className = 'ck-toolbar-wrapper';

            var editableWrapper = document.createElement('div');
            editableWrapper.className = 'ck-editable-wrapper';
            editableWrapper.innerHTML = textarea.value || '';

            wrapper.appendChild(toolbarWrapper);
            wrapper.appendChild(editableWrapper);
            textarea.parentNode.insertBefore(wrapper, textarea);
            textarea.style.display = 'none';

            // Detect if editor should be LTR (for English content)
            var editorDir = textarea.closest('[dir]') ? textarea.closest('[dir]').getAttribute('dir') : 'rtl';
            var editorLang = editorDir === 'ltr' ? 'en' : 'fa';
            var editorPlaceholder = editorDir === 'ltr' ? 'Write your content here...' : 'محتوای خود را اینجا بنویسید...';

            DecoupledEditor
                .create(editableWrapper, {
                    language: editorLang,
                    placeholder: editorPlaceholder,
                    extraPlugins: [UploadAdapterPlugin],
                    image: {
                        toolbar: [
                            'imageTextAlternative',
                            'toggleImageCaption',
                            '|',
                            'imageStyle:inline',
                            'imageStyle:block',
                            'imageStyle:side',
                            '|',
                            'linkImage'
                        ],
                        upload: {
                            types: ['jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']
                        }
                    },
                    mediaEmbed: {
                        previewsInData: true,
                        providers: [
                            {
                                name: 'youtube',
                                url: [
                                    /^(?:m\.)?youtube\.com\/watch\?v=([\w-]+)(?:&t=(\d+))?/,
                                    /^(?:m\.)?youtube\.com\/v\/([\w-]+)(?:\?t=(\d+))?/,
                                    /^youtube\.com\/embed\/([\w-]+)(?:\?start=(\d+))?/,
                                    /^youtu\.be\/([\w-]+)(?:\?t=(\d+))?/
                                ],
                                html: match => {
                                    const id = match[1];
                                    const time = match[2] || 0;
                                    return (
                                        '<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">' +
                                            `<iframe src="https://www.youtube.com/embed/${id}${time ? '?start=' + time : ''}" ` +
                                            'style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;" ' +
                                            'frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>' +
                                        '</div>'
                                    );
                                }
                            },
                            {
                                name: 'twitter',
                                url: [
                                    /^twitter\.com\/([\w]+)\/status\/(\d+)/,
                                    /^x\.com\/([\w]+)\/status\/(\d+)/
                                ],
                                html: match => {
                                    return (
                                        '<blockquote class="twitter-tweet" data-conversation="none">' +
                                            `<a href="https://twitter.com/${match[1]}/status/${match[2]}"></a>` +
                                        '</blockquote>' +
                                        '<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
                                    );
                                }
                            },
                            {
                                name: 'instagram',
                                url: /^instagram\.com\/(?:p|reel)\/([\w-]+)/,
                                html: match => {
                                    return (
                                        '<blockquote class="instagram-media" data-instgrm-captioned ' +
                                        'style="max-width:540px; width:100%;">' +
                                            `<a href="https://www.instagram.com/p/${match[1]}/"></a>` +
                                        '</blockquote>' +
                                        '<script async src="https://www.instagram.com/embed.js"></script>'
                                    );
                                }
                            },
                            {
                                name: 'vimeo',
                                url: [
                                    /^vimeo\.com\/(\d+)/,
                                    /^vimeo\.com\/video\/(\d+)/
                                ],
                                html: match => {
                                    const id = match[1];
                                    return (
                                        '<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">' +
                                            `<iframe src="https://player.vimeo.com/video/${id}" ` +
                                            'style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;" ' +
                                            'frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe>' +
                                        '</div>'
                                    );
                                }
                            },
                            {
                                name: 'spotify',
                                url: [
                                    /^open\.spotify\.com\/(track|album|playlist|episode)\/([\w]+)/
                                ],
                                html: match => {
                                    const type = match[1];
                                    const id = match[2];
                                    return (
                                        `<iframe src="https://open.spotify.com/embed/${type}/${id}" ` +
                                        'width="100%" height="352" frameborder="0" allowtransparency="true" ' +
                                        'allow="encrypted-media"></iframe>'
                                    );
                                }
                            },
                            {
                                name: 'aparat',
                                url: /^aparat\.com\/v\/([\w]+)/,
                                html: match => {
                                    const id = match[1];
                                    return (
                                        '<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">' +
                                            `<iframe src="https://www.aparat.com/video/video/embed/videohash/${id}/vt/frame" ` +
                                            'style="position: absolute; width: 100%; height: 100%; top: 0; left: 0;" ' +
                                            'frameborder="0" allowfullscreen></iframe>' +
                                        '</div>'
                                    );
                                }
                            },
                            {
                                name: 'soundcloud',
                                url: /^soundcloud\.com\/([\w-]+)\/([\w-]+)/,
                                html: match => {
                                    const url = encodeURIComponent(`https://soundcloud.com/${match[1]}/${match[2]}`);
                                    return (
                                        `<iframe width="100%" height="166" scrolling="no" frameborder="no" ` +
                                        `src="https://w.soundcloud.com/player/?url=${url}&color=%237c3aed&auto_play=false"></iframe>`
                                    );
                                }
                            },
                            {
                                name: 'tiktok',
                                url: /^(?:www\.)?tiktok\.com\/@([\w.-]+)\/video\/(\d+)/,
                                html: match => {
                                    return (
                                        '<blockquote class="tiktok-embed" ' +
                                        `cite="https://www.tiktok.com/@${match[1]}/video/${match[2]}" ` +
                                        `data-video-id="${match[2]}" style="max-width: 605px;min-width: 325px;">` +
                                        '</blockquote>' +
                                        '<script async src="https://www.tiktok.com/embed.js"></script>'
                                    );
                                }
                            }
                        ]
                    }
                })
                .then(function(editor) {
                    // Add toolbar
                    toolbarWrapper.appendChild(editor.ui.view.toolbar.element);

                    // Add custom RTL/LTR and alignment buttons
                    addCustomButtons(editor, toolbarWrapper, editableWrapper, textarea);

                    // Add double-click handler for editing images and media
                    addMediaEditHandler(editor, editableWrapper, textarea);

                    textarea.dataset.editorInitialized = 'true';
                    textarea.editorInstance = editor;

                    // Sync content on change (using global cleanEditorContent function)
                    editor.model.document.on('change:data', function() {
                        textarea.value = cleanEditorContent(editor.getData());
                    });

                    // Sync on form submit
                    var form = textarea.closest('form');
                    if (form) {
                        form.addEventListener('submit', function() {
                            textarea.value = cleanEditorContent(editor.getData());
                        });
                    }

                    // Store clean function for external use
                    editor.cleanContent = cleanEditorContent;

                    console.log('DecoupledEditor initialized successfully');
                })
                .catch(function(error) {
                    console.error('Failed to initialize editor:', error);
                    textarea.style.display = '';
                    if (wrapper.parentNode) {
                        wrapper.parentNode.removeChild(wrapper);
                    }
                });
        });
    }

    function addCustomButtons(editor, toolbarWrapper, editableWrapper, textarea) {
        // Create custom button container
        var customBar = document.createElement('div');
        customBar.className = 'ck-custom-buttons';
        customBar.style.cssText = 'display:flex;gap:4px;padding:8px 12px;background:#f8f4ff;border-bottom:1px solid #e2e8f0;direction:ltr;align-items:center;';

        // Button definitions
        var buttons = [
            { id: 'uploadImage', title: 'آپلود تصویر', icon: '🖼️' },
            { id: 'insertEmbed', title: 'درج Embed (یوتیوب، اینستاگرام، ...)', icon: '📺' },
            { id: 'sep0', type: 'separator' },
            { id: 'mediaAlignRight', title: 'تصویر/ویدیو: راست', icon: '⊏▢' },
            { id: 'mediaAlignCenter', title: 'تصویر/ویدیو: وسط', icon: '⊏▢⊐' },
            { id: 'mediaAlignLeft', title: 'تصویر/ویدیو: چپ', icon: '▢⊐' },
            { id: 'sep1', type: 'separator' },
            { id: 'rtl', title: 'راست به چپ (RTL)', icon: '⇐ RTL' },
            { id: 'ltr', title: 'چپ به راست (LTR)', icon: 'LTR ⇒' },
            { id: 'sep2', type: 'separator' },
            { id: 'alignRight', title: 'متن: راست‌چین', icon: '☰⊣' },
            { id: 'alignCenter', title: 'متن: وسط‌چین', icon: '⊢☰⊣' },
            { id: 'alignLeft', title: 'متن: چپ‌چین', icon: '⊢☰' },
            { id: 'alignJustify', title: 'متن: تراز کامل', icon: '☰☰' },
            { id: 'sep3', type: 'separator' },
            { id: 'toggleHtml', title: 'نمایش/ویرایش HTML', icon: '</>' }
        ];

        // Hidden file input for image upload
        var fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.style.display = 'none';
        fileInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                uploadImageFile(file);
            }
            fileInput.value = '';
        });
        document.body.appendChild(fileInput);

        function uploadImageFile(file) {
            var formData = new FormData();
            formData.append('file', file);

            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/admin/api/uploads', true);

            var csrfToken = window.CHELCHELEH_CSRF_TOKEN || '';
            if (csrfToken) {
                xhr.setRequestHeader('X-CSRF-Token', csrfToken);
            }
            xhr.withCredentials = true;

            xhr.onload = function() {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        var response = JSON.parse(xhr.responseText);
                        var imageUrl = response.url || ('/uploads/' + response.uuid);

                        // Insert image into editor
                        editor.model.change(function(writer) {
                            var imageElement = writer.createElement('imageBlock', {
                                src: imageUrl
                            });
                            editor.model.insertContent(imageElement);
                        });
                    } catch (err) {
                        alert('خطا در پردازش پاسخ سرور');
                    }
                } else {
                    var errorMsg = 'خطا در آپلود تصویر';
                    try {
                        var response = JSON.parse(xhr.responseText);
                        errorMsg = response.detail || response.error || errorMsg;
                    } catch (err) {}
                    alert(errorMsg);
                }
            };

            xhr.onerror = function() {
                alert('خطای شبکه در آپلود تصویر');
            };

            xhr.send(formData);
        }

        function showEmbedDialog() {
            // Create modal overlay
            var overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';

            var modal = document.createElement('div');
            modal.style.cssText = 'background:#fff;border-radius:12px;padding:24px;width:90%;max-width:500px;box-shadow:0 20px 40px rgba(0,0,0,0.3);direction:rtl;';
            modal.innerHTML = `
                <h3 style="margin:0 0 16px;font-size:18px;color:#1e293b;">درج Embed از شبکه‌های اجتماعی</h3>
                <p style="margin:0 0 12px;color:#64748b;font-size:14px;">لینک ویدیو یا پست را از یکی از سرویس‌های زیر وارد کنید:</p>
                <ul style="margin:0 0 12px;padding-right:20px;color:#64748b;font-size:12px;line-height:1.6;">
                    <li>YouTube, Vimeo, Aparat</li>
                    <li>Twitter/X, Instagram, TikTok</li>
                    <li>Spotify, SoundCloud</li>
                </ul>
                <input type="text" id="embed-url-input" placeholder="https://..."
                    style="width:100%;padding:12px 16px;border:2px solid #e2e8f0;border-radius:8px;font-size:15px;direction:ltr;box-sizing:border-box;margin-bottom:16px;">

                <div style="margin-bottom:16px;padding:12px;background:#f8fafc;border-radius:8px;">
                    <label style="display:block;margin-bottom:8px;font-size:14px;color:#475569;font-weight:500;">اندازه ویدیو (اختیاری)</label>
                    <div style="display:flex;gap:12px;align-items:center;">
                        <div style="flex:1;">
                            <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">عرض (px یا %)</label>
                            <input type="text" id="embed-width-input" placeholder="مثال: 640 یا 100%"
                                style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                        </div>
                        <div style="flex:1;">
                            <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">ارتفاع (px)</label>
                            <input type="text" id="embed-height-input" placeholder="مثال: 360"
                                style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                        </div>
                    </div>
                    <p style="margin:8px 0 0;font-size:11px;color:#94a3b8;">خالی بگذارید برای اندازه اصلی (پیش‌فرض: عرض کامل با نسبت 16:9)</p>
                </div>

                <div style="display:flex;gap:8px;justify-content:flex-start;">
                    <button type="button" id="embed-insert-btn"
                        style="padding:10px 24px;background:#7c3aed;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;">
                        درج
                    </button>
                    <button type="button" id="embed-cancel-btn"
                        style="padding:10px 24px;background:#f1f5f9;color:#64748b;border:none;border-radius:8px;cursor:pointer;font-size:14px;">
                        انصراف
                    </button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            var urlInput = modal.querySelector('#embed-url-input');
            var widthInput = modal.querySelector('#embed-width-input');
            var heightInput = modal.querySelector('#embed-height-input');
            var insertBtn = modal.querySelector('#embed-insert-btn');
            var cancelBtn = modal.querySelector('#embed-cancel-btn');

            urlInput.focus();

            function closeModal() {
                overlay.remove();
            }

            cancelBtn.onclick = closeModal;
            overlay.onclick = function(e) {
                if (e.target === overlay) closeModal();
            };

            insertBtn.onclick = function() {
                var url = urlInput.value.trim();
                if (!url) {
                    alert('لطفاً یک لینک وارد کنید');
                    return;
                }

                var customWidth = widthInput.value.trim();
                var customHeight = heightInput.value.trim();

                // Try to insert media embed using CKEditor's mediaEmbed command
                try {
                    editor.execute('mediaEmbed', url);

                    // If custom size specified, apply it after insertion
                    if (customWidth || customHeight) {
                        setTimeout(function() {
                            // Find the last inserted media element
                            var mediaElements = editableWrapper.querySelectorAll('figure.media, .ck-media__wrapper');
                            if (mediaElements.length > 0) {
                                var lastMedia = mediaElements[mediaElements.length - 1];
                                var wrapper = lastMedia.closest('figure') || lastMedia;

                                // Apply custom dimensions
                                if (customWidth) {
                                    // Check if it's percentage or pixels
                                    if (customWidth.includes('%')) {
                                        wrapper.style.maxWidth = customWidth;
                                        wrapper.style.width = customWidth;
                                    } else {
                                        var widthVal = parseInt(customWidth, 10);
                                        if (!isNaN(widthVal)) {
                                            wrapper.style.maxWidth = widthVal + 'px';
                                            wrapper.style.width = widthVal + 'px';
                                        }
                                    }
                                }

                                if (customHeight) {
                                    var heightVal = parseInt(customHeight, 10);
                                    if (!isNaN(heightVal)) {
                                        // Find iframe or video container and set height
                                        var iframe = wrapper.querySelector('iframe');
                                        var videoDiv = wrapper.querySelector('div[style*="padding-bottom"]');

                                        if (videoDiv) {
                                            // Remove aspect ratio padding and set fixed height
                                            videoDiv.style.paddingBottom = '0';
                                            videoDiv.style.height = heightVal + 'px';
                                        }
                                        if (iframe) {
                                            iframe.style.height = heightVal + 'px';
                                            iframe.style.position = 'relative';
                                        }
                                    }
                                }

                                // Sync changes (with cleanup)
                                textarea.value = cleanEditorContent(editor.getData());
                            }
                        }, 100);
                    }

                    closeModal();
                } catch (err) {
                    console.error('MediaEmbed error:', err);
                    alert('این لینک پشتیبانی نمی‌شود یا فرمت آن نادرست است');
                }
            };

            urlInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    insertBtn.click();
                } else if (e.key === 'Escape') {
                    closeModal();
                }
            });
        }

        var isHtmlMode = false;
        var htmlTextarea = null;

        var dirSupportEnabled = false;

        function ensureDirSupport() {
            if (dirSupportEnabled) return;
            try {
                editor.model.schema.extend('$block', { allowAttributes: ['dir'] });
                editor.conversion.attributeToAttribute({
                    model: 'dir',
                    view: 'dir'
                });
                dirSupportEnabled = true;
            } catch (e) {
                console.warn('Could not enable dir attribute support:', e);
            }
        }

        function getSelectedParagraph() {
            // Get the DOM element that contains the cursor
            var sel = window.getSelection();
            if (!sel.rangeCount) return null;

            var node = sel.anchorNode;
            // Walk up to find a block element
            while (node && node !== editableWrapper) {
                if (node.nodeType === 1) { // Element node
                    var tagName = node.tagName.toUpperCase();
                    if (['P', 'DIV', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'BLOCKQUOTE'].indexOf(tagName) !== -1) {
                        return node;
                    }
                }
                node = node.parentNode;
            }
            return null;
        }

        function applyAlignment(value) {
            var alignmentCommand = editor.commands.get('alignment');
            if (alignmentCommand) {
                editor.execute('alignment', { value: value });
                return;
            }
            var para = getSelectedParagraph();
            if (!para) {
                alert('لطفاً ابتدا روی یک پاراگراف کلیک کنید');
                return;
            }

            var classes = [
                'text-align-right',
                'text-align-left',
                'text-align-center',
                'text-align-justify'
            ];
            classes.forEach(function(cls) { para.classList.remove(cls); });
            para.classList.add('text-align-' + value);

            var content = cleanEditorContent(editableWrapper.innerHTML);
            editor.setData(content);
            textarea.value = content;
        }

        function applyMediaAlignment(alignment) {
            // Get selected element from CKEditor model
            var selection = editor.model.document.selection;
            var selectedElement = selection.getSelectedElement();

            // Check if an image is selected
            if (selectedElement && (selectedElement.name === 'imageBlock' || selectedElement.name === 'imageInline')) {
                // Map alignment to CKEditor image style
                var styleMap = {
                    'right': 'alignRight',
                    'center': 'alignCenter',
                    'left': 'alignLeft'
                };
                var styleName = styleMap[alignment];
                if (styleName) {
                    try {
                        editor.execute('imageStyle', { value: styleName });
                        return;
                    } catch (e) {
                        console.warn('imageStyle command failed:', e);
                    }
                }
            }

            // Check if a media embed is selected
            if (selectedElement && selectedElement.name === 'media') {
                // For media embeds, we need to wrap in a div with alignment
                var viewElement = editor.editing.mapper.toViewElement(selectedElement);
                if (viewElement) {
                    var domElement = editor.editing.view.domConverter.mapViewToDom(viewElement);
                    if (domElement) {
                        // Apply alignment via inline style
                        var wrapper = domElement.closest('figure') || domElement;
                        wrapper.style.textAlign = alignment;
                        wrapper.style.display = 'block';
                        if (alignment === 'center') {
                            wrapper.style.marginLeft = 'auto';
                            wrapper.style.marginRight = 'auto';
                        } else if (alignment === 'right') {
                            wrapper.style.marginLeft = 'auto';
                            wrapper.style.marginRight = '0';
                        } else {
                            wrapper.style.marginLeft = '0';
                            wrapper.style.marginRight = 'auto';
                        }
                        // Sync to textarea
                        textarea.value = cleanEditorContent(editor.getData());
                        return;
                    }
                }
            }

            // Fallback: try to find and align image/media in DOM
            var sel = window.getSelection();
            if (sel.rangeCount) {
                var node = sel.anchorNode;
                while (node && node !== editableWrapper) {
                    if (node.nodeType === 1) {
                        var tagName = node.tagName.toUpperCase();
                        if (tagName === 'FIGURE' || tagName === 'IMG' || node.classList.contains('media')) {
                            var target = tagName === 'IMG' ? node.closest('figure') || node : node;

                            // Remove existing alignment classes
                            target.classList.remove('image-align-left', 'image-align-center', 'image-align-right');
                            target.classList.add('image-align-' + alignment);

                            // Also apply inline styles for immediate effect
                            if (alignment === 'center') {
                                target.style.marginLeft = 'auto';
                                target.style.marginRight = 'auto';
                                target.style.display = 'block';
                                target.style.float = 'none';
                            } else if (alignment === 'right') {
                                target.style.float = 'right';
                                target.style.marginLeft = '1em';
                                target.style.marginRight = '0';
                            } else {
                                target.style.float = 'left';
                                target.style.marginRight = '1em';
                                target.style.marginLeft = '0';
                            }

                            // Sync changes
                            var content = cleanEditorContent(editableWrapper.innerHTML);
                            editor.setData(content);
                            textarea.value = content;
                            return;
                        }
                    }
                    node = node.parentNode;
                }
            }

            alert('لطفاً ابتدا روی یک تصویر یا ویدیو کلیک کنید');
        }

        function applyDirection(dir) {
            ensureDirSupport();
            var blocks = Array.from(editor.model.document.selection.getSelectedBlocks());
            if (!blocks.length) {
                alert('لطفاً ابتدا روی یک پاراگراف کلیک کنید');
                return;
            }

            editor.model.change(function(writer) {
                blocks.forEach(function(block) {
                    writer.setAttribute('dir', dir, block);
                });
            });

            var alignmentCommand = editor.commands.get('alignment');
            if (alignmentCommand) {
                editor.execute('alignment', { value: dir === 'rtl' ? 'right' : 'left' });
            } else {
                applyAlignment(dir === 'rtl' ? 'right' : 'left');
            }
        }

        function toggleHtmlMode(wrapper) {
            if (!isHtmlMode) {
                // Switch to HTML mode
                var content = editor.getData();

                // Create HTML textarea
                htmlTextarea = document.createElement('textarea');
                htmlTextarea.value = content;
                htmlTextarea.style.cssText = 'width:100%;min-height:350px;max-height:600px;padding:16px;font-family:monospace;font-size:14px;line-height:1.6;border:none;resize:vertical;direction:ltr;background:#1e293b;color:#e2e8f0;';
                htmlTextarea.placeholder = 'HTML code here...';

                // Hide CKEditor, show textarea
                editableWrapper.style.display = 'none';
                wrapper.querySelector('.ck-toolbar-wrapper .ck-toolbar').style.display = 'none';
                wrapper.appendChild(htmlTextarea);
                htmlTextarea.focus();

                isHtmlMode = true;
            } else {
                // Switch back to visual mode
                var htmlContent = cleanEditorContent(htmlTextarea.value);

                // Update editor with new content
                editor.setData(htmlContent);
                textarea.value = htmlContent;

                // Remove textarea, show CKEditor
                htmlTextarea.remove();
                htmlTextarea = null;
                editableWrapper.style.display = '';
                wrapper.querySelector('.ck-toolbar-wrapper .ck-toolbar').style.display = '';

                isHtmlMode = false;
            }
        }

        function handleButtonClick(btnId, wrapper) {
            switch(btnId) {
                case 'uploadImage':
                    if (!isHtmlMode) fileInput.click();
                    break;
                case 'insertEmbed':
                    if (!isHtmlMode) showEmbedDialog();
                    break;
                case 'mediaAlignRight':
                    if (!isHtmlMode) applyMediaAlignment('right');
                    break;
                case 'mediaAlignCenter':
                    if (!isHtmlMode) applyMediaAlignment('center');
                    break;
                case 'mediaAlignLeft':
                    if (!isHtmlMode) applyMediaAlignment('left');
                    break;
                case 'rtl':
                    if (!isHtmlMode) applyDirection('rtl');
                    break;
                case 'ltr':
                    if (!isHtmlMode) applyDirection('ltr');
                    break;
                case 'alignRight':
                    if (!isHtmlMode) applyAlignment('right');
                    break;
                case 'alignCenter':
                    if (!isHtmlMode) applyAlignment('center');
                    break;
                case 'alignLeft':
                    if (!isHtmlMode) applyAlignment('left');
                    break;
                case 'alignJustify':
                    if (!isHtmlMode) applyAlignment('justify');
                    break;
                case 'toggleHtml':
                    toggleHtmlMode(wrapper);
                    break;
            }
        }

        buttons.forEach(function(btn) {
            if (btn.type === 'separator') {
                var sep = document.createElement('span');
                sep.style.cssText = 'width:1px;height:24px;background:#c4b5fd;margin:0 6px;';
                customBar.appendChild(sep);
                return;
            }

            var button = document.createElement('button');
            button.type = 'button';
            button.title = btn.title;
            button.textContent = btn.icon;
            button.style.cssText = 'padding:6px 12px;border:1px solid #d4d4d8;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;font-weight:500;transition:all 0.15s;';
            button.onmouseover = function() {
                this.style.background = '#ede9fe';
                this.style.borderColor = '#a78bfa';
            };
            button.onmouseout = function() {
                this.style.background = '#fff';
                this.style.borderColor = '#d4d4d8';
            };
            button.onmousedown = function(e) {
                e.preventDefault(); // Prevent losing focus from editor
            };
            button.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                handleButtonClick(btn.id, toolbarWrapper.parentNode);
            };
            customBar.appendChild(button);
        });

        // Insert custom buttons before the CKEditor toolbar
        toolbarWrapper.insertBefore(customBar, toolbarWrapper.firstChild);
    }

    function addMediaEditHandler(editor, editableWrapper, textarea) {
        // Double-click on images or media to edit
        editableWrapper.addEventListener('dblclick', function(e) {
            var target = e.target;

            // Find the figure or media element
            var figure = target.closest('figure');
            var img = target.closest('img') || (figure && figure.querySelector('img'));
            var mediaWrapper = target.closest('.media') || target.closest('figure.media');
            var iframe = target.closest('iframe') || (mediaWrapper && mediaWrapper.querySelector('iframe'));

            if (img && !mediaWrapper) {
                // Image edit dialog
                showImageEditDialog(editor, editableWrapper, textarea, figure || img, img);
            } else if (mediaWrapper || iframe) {
                // Media/Video edit dialog
                showMediaEditDialog(editor, editableWrapper, textarea, mediaWrapper || figure, iframe);
            }
        });
    }

    function showImageEditDialog(editor, editableWrapper, textarea, figure, img) {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';

        // Get current values
        var currentAlt = img.alt || '';
        var currentWidth = img.style.width || img.getAttribute('width') || '';
        var currentHeight = img.style.height || img.getAttribute('height') || '';

        // Get natural dimensions for reference
        var naturalWidth = img.naturalWidth || 0;
        var naturalHeight = img.naturalHeight || 0;

        // Detect current alignment
        var currentAlign = '';
        var targetEl = figure || img;
        if (targetEl.classList.contains('image-align-left') || targetEl.style.float === 'left') {
            currentAlign = 'left';
        } else if (targetEl.classList.contains('image-align-right') || targetEl.style.float === 'right') {
            currentAlign = 'right';
        } else if (targetEl.classList.contains('image-align-center') ||
                   (targetEl.style.marginLeft === 'auto' && targetEl.style.marginRight === 'auto')) {
            currentAlign = 'center';
        }

        var modal = document.createElement('div');
        modal.style.cssText = 'background:#fff;border-radius:12px;padding:24px;width:90%;max-width:520px;box-shadow:0 20px 40px rgba(0,0,0,0.3);direction:rtl;';
        modal.innerHTML = `
            <h3 style="margin:0 0 20px;font-size:18px;color:#1e293b;display:flex;align-items:center;gap:8px;">
                <span style="font-size:24px;">🖼️</span> ویرایش تصویر
            </h3>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:14px;color:#475569;margin-bottom:6px;font-weight:500;">متن جایگزین (Alt Text)</label>
                <input type="text" id="edit-img-alt" value="${currentAlt.replace(/"/g, '&quot;')}"
                    placeholder="توضیح تصویر برای دسترسی‌پذیری و سئو"
                    style="width:100%;padding:10px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;box-sizing:border-box;">
            </div>

            <div style="margin-bottom:16px;padding:14px;background:#f8fafc;border-radius:8px;">
                <label style="display:block;font-size:14px;color:#475569;margin-bottom:10px;font-weight:500;">اندازه تصویر</label>
                ${naturalWidth > 0 ? `<p style="margin:0 0 10px;font-size:12px;color:#64748b;">اندازه اصلی: ${naturalWidth}×${naturalHeight} پیکسل</p>` : ''}

                <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
                    <button type="button" class="size-preset-btn" data-size="25"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۲۵٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="50"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۵۰٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="75"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۷۵٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="100"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۱۰۰٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="original"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        اصلی
                    </button>
                </div>

                <div style="display:flex;gap:12px;align-items:end;">
                    <div style="flex:1;">
                        <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">عرض (px یا %)</label>
                        <input type="text" id="edit-img-width" value="${currentWidth}"
                            placeholder="مثال: 400 یا 50%"
                            style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                    </div>
                    <div style="flex:1;">
                        <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">ارتفاع (px یا auto)</label>
                        <input type="text" id="edit-img-height" value="${currentHeight}"
                            placeholder="auto"
                            style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                    </div>
                    <label style="display:flex;align-items:center;gap:6px;cursor:pointer;white-space:nowrap;">
                        <input type="checkbox" id="edit-img-ratio" checked style="width:16px;height:16px;">
                        <span style="font-size:12px;color:#64748b;">حفظ نسبت</span>
                    </label>
                </div>
            </div>

            <div style="margin-bottom:20px;">
                <label style="display:block;font-size:14px;color:#475569;margin-bottom:8px;font-weight:500;">تراز تصویر</label>
                <div style="display:flex;gap:8px;">
                    <button type="button" class="align-btn" data-align="right"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'right' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'right' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ⊏▢ راست‌چین
                    </button>
                    <button type="button" class="align-btn" data-align="center"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'center' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'center' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ⊏▢⊐ وسط‌چین
                    </button>
                    <button type="button" class="align-btn" data-align="left"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'left' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'left' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ▢⊐ چپ‌چین
                    </button>
                </div>
            </div>

            <div style="display:flex;gap:8px;justify-content:flex-start;">
                <button type="button" id="edit-img-save"
                    style="padding:10px 24px;background:#7c3aed;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;">
                    ذخیره تغییرات
                </button>
                <button type="button" id="edit-img-cancel"
                    style="padding:10px 24px;background:#f1f5f9;color:#64748b;border:none;border-radius:8px;cursor:pointer;font-size:14px;">
                    انصراف
                </button>
                <button type="button" id="edit-img-delete"
                    style="padding:10px 24px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:8px;cursor:pointer;font-size:14px;margin-right:auto;">
                    حذف تصویر
                </button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        var selectedAlign = currentAlign;
        var widthInput = modal.querySelector('#edit-img-width');
        var heightInput = modal.querySelector('#edit-img-height');
        var ratioCheckbox = modal.querySelector('#edit-img-ratio');

        // Size preset buttons
        var sizePresetBtns = modal.querySelectorAll('.size-preset-btn');
        sizePresetBtns.forEach(function(btn) {
            btn.onclick = function() {
                var size = this.dataset.size;
                if (size === 'original') {
                    widthInput.value = '';
                    heightInput.value = '';
                } else {
                    widthInput.value = size + '%';
                    heightInput.value = 'auto';
                }
                // Highlight selected
                sizePresetBtns.forEach(function(b) {
                    b.style.borderColor = '#e2e8f0';
                    b.style.background = '#fff';
                });
                this.style.borderColor = '#7c3aed';
                this.style.background = '#f3e8ff';
            };
        });

        // Keep aspect ratio when width changes
        widthInput.addEventListener('input', function() {
            if (ratioCheckbox.checked && naturalWidth > 0 && naturalHeight > 0) {
                var val = this.value.trim();
                if (val && !val.includes('%')) {
                    var w = parseInt(val, 10);
                    if (!isNaN(w)) {
                        var h = Math.round(w * naturalHeight / naturalWidth);
                        heightInput.value = h + 'px';
                    }
                } else if (val.includes('%')) {
                    heightInput.value = 'auto';
                }
            }
        });

        // Alignment buttons
        var alignBtns = modal.querySelectorAll('.align-btn');
        alignBtns.forEach(function(btn) {
            btn.onclick = function() {
                alignBtns.forEach(function(b) {
                    b.style.borderColor = '#e2e8f0';
                    b.style.background = '#fff';
                });
                this.style.borderColor = '#7c3aed';
                this.style.background = '#f3e8ff';
                selectedAlign = this.dataset.align;
            };
        });

        function closeModal() {
            overlay.remove();
        }

        modal.querySelector('#edit-img-cancel').onclick = closeModal;
        overlay.onclick = function(e) {
            if (e.target === overlay) closeModal();
        };

        modal.querySelector('#edit-img-delete').onclick = function() {
            if (confirm('آیا از حذف این تصویر مطمئن هستید؟')) {
                if (figure) {
                    figure.remove();
                } else {
                    img.remove();
                }
                // Save directly to textarea first, then sync (with cleanup)
                textarea.value = cleanEditorContent(editableWrapper.innerHTML);
                editor.setData(textarea.value);
                closeModal();
            }
        };

        modal.querySelector('#edit-img-save').onclick = function() {
            var newAlt = modal.querySelector('#edit-img-alt').value;
            var newWidth = widthInput.value.trim();
            var newHeight = heightInput.value.trim();

            // Apply alt text
            img.alt = newAlt;

            // Apply dimensions to img element
            if (newWidth) {
                var widthVal = newWidth;
                if (!newWidth.includes('%') && !newWidth.includes('px')) {
                    widthVal = newWidth + 'px';
                }
                img.style.width = widthVal;
                img.setAttribute('width', newWidth.replace('px', '').replace('%', ''));
            } else {
                img.style.width = '';
                img.removeAttribute('width');
            }

            if (newHeight && newHeight !== 'auto') {
                var heightVal = newHeight;
                if (!newHeight.includes('%') && !newHeight.includes('px')) {
                    heightVal = newHeight + 'px';
                }
                img.style.height = heightVal;
                img.setAttribute('height', newHeight.replace('px', '').replace('%', ''));
            } else {
                img.style.height = 'auto';
                img.removeAttribute('height');
            }

            // Apply alignment to figure or img
            var alignTarget = figure || img;

            // Clear all existing alignment
            alignTarget.classList.remove('image-align-left', 'image-align-center', 'image-align-right');
            alignTarget.classList.remove('image-style-side', 'image-style-align-left', 'image-style-align-right', 'image-style-align-center');
            alignTarget.style.float = '';
            alignTarget.style.marginLeft = '';
            alignTarget.style.marginRight = '';
            alignTarget.style.display = '';

            if (selectedAlign === 'left') {
                alignTarget.classList.add('image-align-left');
                alignTarget.style.float = 'left';
                alignTarget.style.marginRight = '1.5em';
                alignTarget.style.marginLeft = '0';
            } else if (selectedAlign === 'right') {
                alignTarget.classList.add('image-align-right');
                alignTarget.style.float = 'right';
                alignTarget.style.marginLeft = '1.5em';
                alignTarget.style.marginRight = '0';
            } else if (selectedAlign === 'center') {
                alignTarget.classList.add('image-align-center');
                alignTarget.style.float = 'none';
                alignTarget.style.display = 'block';
                alignTarget.style.marginLeft = 'auto';
                alignTarget.style.marginRight = 'auto';
            }

            // Important: Save directly to textarea FIRST, then tell CKEditor (with cleanup)
            textarea.value = cleanEditorContent(editableWrapper.innerHTML);

            // Update CKEditor's internal state
            try {
                editor.setData(textarea.value);
            } catch (e) {
                console.warn('Could not sync to CKEditor:', e);
            }

            closeModal();
        };
    }

    function showMediaEditDialog(editor, editableWrapper, textarea, mediaWrapper, iframe) {
        var overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';

        // Get current values
        var currentWidth = mediaWrapper ? (mediaWrapper.style.width || mediaWrapper.style.maxWidth || '') : '';
        var currentHeight = '';
        if (iframe) {
            currentHeight = iframe.style.height || iframe.getAttribute('height') || '';
        }
        var videoDiv = mediaWrapper ? mediaWrapper.querySelector('div[style*="padding-bottom"]') : null;

        // Detect current alignment
        var currentAlign = '';
        if (mediaWrapper) {
            if (mediaWrapper.classList.contains('image-align-left') || mediaWrapper.style.float === 'left') {
                currentAlign = 'left';
            } else if (mediaWrapper.classList.contains('image-align-right') || mediaWrapper.style.float === 'right') {
                currentAlign = 'right';
            } else if (mediaWrapper.classList.contains('image-align-center') ||
                       (mediaWrapper.style.marginLeft === 'auto' && mediaWrapper.style.marginRight === 'auto')) {
                currentAlign = 'center';
            }
        }

        var modal = document.createElement('div');
        modal.style.cssText = 'background:#fff;border-radius:12px;padding:24px;width:90%;max-width:520px;box-shadow:0 20px 40px rgba(0,0,0,0.3);direction:rtl;';
        modal.innerHTML = `
            <h3 style="margin:0 0 20px;font-size:18px;color:#1e293b;display:flex;align-items:center;gap:8px;">
                <span style="font-size:24px;">📺</span> ویرایش ویدیو
            </h3>

            <div style="margin-bottom:16px;padding:14px;background:#f8fafc;border-radius:8px;">
                <label style="display:block;font-size:14px;color:#475569;margin-bottom:10px;font-weight:500;">اندازه ویدیو</label>

                <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
                    <button type="button" class="size-preset-btn" data-size="50"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۵۰٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="75"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۷۵٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="100"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        ۱۰۰٪
                    </button>
                    <button type="button" class="size-preset-btn" data-size="640"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        640px
                    </button>
                    <button type="button" class="size-preset-btn" data-size="854"
                        style="padding:8px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;">
                        854px
                    </button>
                </div>

                <div style="display:flex;gap:12px;">
                    <div style="flex:1;">
                        <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">عرض (px یا %)</label>
                        <input type="text" id="edit-media-width" value="${currentWidth}"
                            placeholder="مثال: 640 یا 100%"
                            style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                    </div>
                    <div style="flex:1;">
                        <label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;">ارتفاع (px)</label>
                        <input type="text" id="edit-media-height" value="${currentHeight}"
                            placeholder="مثال: 360"
                            style="width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;direction:ltr;box-sizing:border-box;">
                    </div>
                </div>
                <p style="margin:8px 0 0;font-size:11px;color:#94a3b8;">نسبت استاندارد ۱۶:۹ - برای عرض 640 ارتفاع 360 و برای عرض 854 ارتفاع 480</p>
            </div>

            <div style="margin-bottom:20px;">
                <label style="display:block;font-size:14px;color:#475569;margin-bottom:8px;font-weight:500;">تراز ویدیو</label>
                <div style="display:flex;gap:8px;">
                    <button type="button" class="align-btn" data-align="right"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'right' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'right' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ⊏▢ راست‌چین
                    </button>
                    <button type="button" class="align-btn" data-align="center"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'center' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'center' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ⊏▢⊐ وسط‌چین
                    </button>
                    <button type="button" class="align-btn" data-align="left"
                        style="flex:1;padding:12px;border:2px solid ${currentAlign === 'left' ? '#7c3aed' : '#e2e8f0'};border-radius:8px;background:${currentAlign === 'left' ? '#f3e8ff' : '#fff'};cursor:pointer;font-size:13px;transition:all 0.15s;">
                        ▢⊐ چپ‌چین
                    </button>
                </div>
            </div>

            <div style="display:flex;gap:8px;justify-content:flex-start;">
                <button type="button" id="edit-media-save"
                    style="padding:10px 24px;background:#7c3aed;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;">
                    ذخیره تغییرات
                </button>
                <button type="button" id="edit-media-cancel"
                    style="padding:10px 24px;background:#f1f5f9;color:#64748b;border:none;border-radius:8px;cursor:pointer;font-size:14px;">
                    انصراف
                </button>
                <button type="button" id="edit-media-delete"
                    style="padding:10px 24px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:8px;cursor:pointer;font-size:14px;margin-right:auto;">
                    حذف ویدیو
                </button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        var selectedAlign = currentAlign;
        var widthInput = modal.querySelector('#edit-media-width');
        var heightInput = modal.querySelector('#edit-media-height');

        // Size preset buttons
        var sizePresetBtns = modal.querySelectorAll('.size-preset-btn');
        sizePresetBtns.forEach(function(btn) {
            btn.onclick = function() {
                var size = this.dataset.size;
                if (size === '50' || size === '75' || size === '100') {
                    widthInput.value = size + '%';
                    heightInput.value = '';
                } else if (size === '640') {
                    widthInput.value = '640px';
                    heightInput.value = '360px';
                } else if (size === '854') {
                    widthInput.value = '854px';
                    heightInput.value = '480px';
                }
                // Highlight selected
                sizePresetBtns.forEach(function(b) {
                    b.style.borderColor = '#e2e8f0';
                    b.style.background = '#fff';
                });
                this.style.borderColor = '#7c3aed';
                this.style.background = '#f3e8ff';
            };
        });

        // Alignment buttons
        var alignBtns = modal.querySelectorAll('.align-btn');
        alignBtns.forEach(function(btn) {
            btn.onclick = function() {
                alignBtns.forEach(function(b) {
                    b.style.borderColor = '#e2e8f0';
                    b.style.background = '#fff';
                });
                this.style.borderColor = '#7c3aed';
                this.style.background = '#f3e8ff';
                selectedAlign = this.dataset.align;
            };
        });

        function closeModal() {
            overlay.remove();
        }

        modal.querySelector('#edit-media-cancel').onclick = closeModal;
        overlay.onclick = function(e) {
            if (e.target === overlay) closeModal();
        };

        modal.querySelector('#edit-media-delete').onclick = function() {
            if (confirm('آیا از حذف این ویدیو مطمئن هستید؟')) {
                if (mediaWrapper) {
                    mediaWrapper.remove();
                }
                textarea.value = cleanEditorContent(editableWrapper.innerHTML);
                editor.setData(textarea.value);
                closeModal();
            }
        };

        modal.querySelector('#edit-media-save').onclick = function() {
            var newWidth = widthInput.value.trim();
            var newHeight = heightInput.value.trim();

            // Apply dimensions
            if (mediaWrapper) {
                if (newWidth) {
                    var widthValue = newWidth;
                    if (!newWidth.includes('%') && !newWidth.includes('px')) {
                        widthValue = newWidth + 'px';
                    }
                    mediaWrapper.style.width = widthValue;
                    mediaWrapper.style.maxWidth = widthValue;
                } else {
                    mediaWrapper.style.width = '';
                    mediaWrapper.style.maxWidth = '';
                }
            }

            if (newHeight && iframe) {
                var heightValue = newHeight;
                if (!newHeight.includes('px')) {
                    heightValue = parseInt(newHeight, 10);
                    if (!isNaN(heightValue)) {
                        heightValue = heightValue + 'px';
                    }
                }
                if (videoDiv) {
                    videoDiv.style.paddingBottom = '0';
                    videoDiv.style.height = heightValue;
                }
                iframe.style.height = heightValue;
                iframe.style.position = 'relative';
            }

            // Apply alignment
            if (mediaWrapper) {
                // Clear existing alignment
                mediaWrapper.classList.remove('image-align-left', 'image-align-center', 'image-align-right');
                mediaWrapper.style.float = '';
                mediaWrapper.style.marginLeft = '';
                mediaWrapper.style.marginRight = '';
                mediaWrapper.style.display = '';

                if (selectedAlign === 'left') {
                    mediaWrapper.classList.add('image-align-left');
                    mediaWrapper.style.float = 'left';
                    mediaWrapper.style.marginRight = '1.5em';
                    mediaWrapper.style.marginLeft = '0';
                } else if (selectedAlign === 'right') {
                    mediaWrapper.classList.add('image-align-right');
                    mediaWrapper.style.float = 'right';
                    mediaWrapper.style.marginLeft = '1.5em';
                    mediaWrapper.style.marginRight = '0';
                } else if (selectedAlign === 'center') {
                    mediaWrapper.classList.add('image-align-center');
                    mediaWrapper.style.float = 'none';
                    mediaWrapper.style.display = 'block';
                    mediaWrapper.style.marginLeft = 'auto';
                    mediaWrapper.style.marginRight = 'auto';
                }
            }

            // Important: Save directly to textarea FIRST, then tell CKEditor (with cleanup)
            textarea.value = cleanEditorContent(editableWrapper.innerHTML);

            // Update CKEditor's internal state
            try {
                editor.setData(textarea.value);
            } catch (e) {
                console.warn('Could not sync to CKEditor:', e);
            }

            closeModal();
        };
    }

    // Initialize after DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEditors);
    } else {
        initEditors();
    }
})();
