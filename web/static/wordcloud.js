// 词云生成器交互逻辑
document.addEventListener('DOMContentLoaded', function() {
    // 模式选项卡切换
    const modeTabs = document.querySelectorAll('.mode-tab');
    const modeInput = document.getElementById('mode');
    const panels = {
        shape: document.getElementById('shapePanel'),
        icon: document.getElementById('iconPanel'),
        image: document.getElementById('imagePanel'),
        character: document.getElementById('characterPanel'),
        random: null   // 随机模式没有额外配置面板
    };

    function switchMode(mode) {
        // 更新隐藏域
        modeInput.value = mode;
        // 更新选项卡样式
        modeTabs.forEach(tab => {
            if (tab.dataset.mode === mode) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        // 显示/隐藏对应面板
        for (const [key, panel] of Object.entries(panels)) {
            if (panel) {
                panel.style.display = (key === mode) ? 'block' : 'none';
            }
        }
    }

    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchMode(tab.dataset.mode);
        });
    });
    // 初始激活随机模式（默认）
    switchMode('random');

    // 字符预设
    const chars = ['福', '寿', '喜', '乐', '安', '康'];
    const charContainer = document.getElementById('charPresets');
    if (charContainer) {
        chars.forEach(ch => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'preset-btn';
            btn.textContent = ch;
            btn.addEventListener('click', () => {
                document.getElementById('customChar').value = ch;
            });
            charContainer.appendChild(btn);
        });
    }

    let allIcons = [];
    let allImages = [];

    function renderIconPresets(icons) {
        const container = document.getElementById('iconPresetsList');
        if (!container) return;
        container.innerHTML = '';
        icons.forEach(filename => {
            const baseName = filename.split('.').slice(0, -1).join('.');
            const imgUrl = `/data/masks/icon_masks/${filename}`;
            const div = document.createElement('div');
            div.className = 'preset-image-item';
            div.innerHTML = `
                <img src="${imgUrl}"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'50\' height=\'50\' viewBox=\'0 0 24 24\' fill=\'%23e2e8f0\'%3E%3Crect width=\'24\' height=\'24\'/%3E%3Ctext x=\'12\' y=\'16\' text-anchor=\'middle\' fill=\'%23999\'%3E?%3C/text%3E%3C/svg%3E'">
            `;
            div.addEventListener('click', () => {
                document.querySelectorAll('#iconPresetsList .preset-image-item').forEach(item => item.classList.remove('active'));
                div.classList.add('active');
                document.getElementById('iconName').value = baseName;
                document.getElementById('customIconImage').value = '';
                document.getElementById('customIconPreview').style.display = 'none';
            });
            container.appendChild(div);
        });
    }

    function renderImagePresets(images) {
        const container = document.getElementById('presetImagesList');
        if (!container) return;
        container.innerHTML = '';
        images.forEach(filename => {
            const baseName = filename.split('.').slice(0, -1).join('.');
            const imgUrl = `/data/masks/mask_presets/${filename}`;
            const div = document.createElement('div');
            div.className = 'preset-image-item';
            div.innerHTML = `
                <img src="${imgUrl}"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'50\' height=\'50\' viewBox=\'0 0 24 24\' fill=\'%23e2e8f0\'%3E%3Crect width=\'24\' height=\'24\'/%3E%3Ctext x=\'12\' y=\'16\' text-anchor=\'middle\' fill=\'%23999\'%3E?%3C/text%3E%3C/svg%3E'">
            `;
            div.addEventListener('click', () => {
                document.querySelectorAll('#presetImagesList .preset-image-item').forEach(item => item.classList.remove('active'));
                div.classList.add('active');
                document.getElementById('presetImage').value = filename;
                document.getElementById('customImage').value = '';
                document.getElementById('customImagePreview').style.display = 'none';
            });
            container.appendChild(div);
        });
    }

    function refreshIconPresets() {
        fetch('/api/icon-masks')
            .then(res => res.json())
            .then(data => {
                allIcons = data;
                renderIconPresets(allIcons);
            }).catch(console.warn);
    }

    function refreshImagePresets() {
        fetch('/api/mask-presets')
            .then(res => res.json())
            .then(data => {
                allImages = data.images || [];
                renderImagePresets(allImages);
            }).catch(console.warn);
    }

    refreshIconPresets();
    refreshImagePresets();

    const customIconInput = document.getElementById('customIconImage');
    if (customIconInput) {
        customIconInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('customIconPreviewImg').src = e.target.result;
                    document.getElementById('customIconPreview').style.display = 'block';
                };
                reader.readAsDataURL(file);
                document.querySelectorAll('#iconPresetsList .preset-image-item').forEach(item => item.classList.remove('active'));
                document.getElementById('iconName').value = '';
            } else {
                document.getElementById('customIconPreview').style.display = 'none';
            }
        });
    }

    const customImageInput = document.getElementById('customImage');
    if (customImageInput) {
        customImageInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('customPreviewImg').src = e.target.result;
                    document.getElementById('customImagePreview').style.display = 'block';
                };
                reader.readAsDataURL(file);
                document.querySelectorAll('#presetImagesList .preset-image-item').forEach(item => item.classList.remove('active'));
                document.getElementById('presetImage').value = '';
            } else {
                document.getElementById('customImagePreview').style.display = 'none';
            }
        });
    }

    const form = document.getElementById('wcForm');
    const previewCard = document.getElementById('previewCard');
    let currentImageUrl = '';

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        previewCard.innerHTML = `<div class="loading-state"><i class="fas fa-spinner fa-pulse fa-2x"></i><p>正在生成词云，请稍后...</p></div>`;
        const formData = new FormData(form);
        const mode = modeInput.value;

        if (mode === 'icon' && document.getElementById('customIconImage').files.length > 0) {
            formData.delete('icon_name');
        }
        if (mode === 'image' && document.getElementById('customImage').files.length > 0) {
            formData.delete('preset_image');
        }

        try {
            const response = await fetch('/api/generate-wordcloud', { method: 'POST', body: formData });
            const data = await response.json();
            if (response.ok && data.image_url) {
                currentImageUrl = data.image_url;
                previewCard.innerHTML = `
                    <img src="${currentImageUrl}" alt="词云预览图">
                    <button id="downloadBtn" class="download-btn"><i class="fas fa-download"></i> 下载图片 (PNG)</button>
                `;
                document.getElementById('downloadBtn').addEventListener('click', () => {
                    if (currentImageUrl) {
                        const a = document.createElement('a');
                        a.href = currentImageUrl;
                        a.download = `wordcloud_${Date.now()}.png`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    }
                });
                if (data.new_icon) {
                    refreshIconPresets();
                }
                if (data.new_image) {
                    refreshImagePresets();
                }
            } else {
                previewCard.innerHTML = `<div class="loading-state"><i class="fas fa-exclamation-triangle"></i><p>生成失败: ${data.error || '未知错误'}</p></div>`;
            }
        } catch (err) {
            previewCard.innerHTML = `<div class="loading-state"><i class="fas fa-exclamation-triangle"></i><p>请求错误: ${err.message}</p></div>`;
        }
    });
});