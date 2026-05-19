// ==================== 全局变量 ====================
let currentPage = 1;
let currentSearch = '';
let totalPages = 1;
let currentEditFontName = '';
let currentDetailFontName = '';
let currentDetailCustomInfo = {};

// 登录模态框元素
const loginModal = document.getElementById('loginModal');
const closeLogin = document.querySelector('.close-login');
let pendingAction = null; // 存储登录成功后要执行的操作

// ==================== 工具函数 ====================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    }).replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, function(c) {
        return c;
    });
}

function extractDisplayNameFromBasename(basename) {
    if (basename.includes('／')) {
        // 取斜杠后的部分（中文）
        return basename.split('／')[1];
    }
    return basename;
}

function basenameWithoutExt(filename) {
    const lastDot = filename.lastIndexOf('.');
    if (lastDot === -1) return filename;
    return filename.substring(0, lastDot);
}

// ==================== 首页逻辑 ====================
function loadFonts() {
    const grid = document.getElementById('cardGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-pulse"></i> 加载中...</div>';

    fetch(`/api/fonts?page=${currentPage}&per_page=20&search=${encodeURIComponent(currentSearch)}`)
        .then(res => res.json())
        .then(data => {
            totalPages = data.total_pages;
            renderCards(data.fonts);
            renderPagination();
        })
        .catch(err => {
            console.error(err);
            grid.innerHTML = '<div class="loading">加载失败，请刷新重试</div>';
        });
}

// 辅助函数：去除文件名最后一个点及之后的扩展名
function basenameWithoutExt(filename) {
    const lastDot = filename.lastIndexOf('.');
    if (lastDot === -1) return filename;
    return filename.substring(0, lastDot);
}

function renderCards(fonts) {
    const grid = document.getElementById('cardGrid');
    if (!fonts.length) {
        grid.innerHTML = '<div class="loading">😢 没有找到字体</div>';
        return;
    }

    let html = '';
    for (const font of fonts) {
        const customInfo = font.custom_info || {};
        const baseName = basenameWithoutExt(font.font_name);
        // 显示名称：优先自定义，否则用元数据中的族名，最后用文件名中的中文部分
        let displayName = customInfo.custom_font_name || font.display_name;
        if (!displayName) {
            displayName = baseName.includes('／') ? baseName.split('／')[1] : baseName;
        }
        displayName = displayName.replace(/／/g, '|');
        const previewUrl = `/preview/${baseName}_preview.png`;
        const ext = font.font_name.split('.').pop().toUpperCase();
        const licenseClass = font.final_license;
        const licenseText = licenseClass ? licenseClass.toUpperCase() : 'UNKNOWN';

        html += `
            <div class="card" data-font-name="${escapeHtml(font.font_name)}"
                 data-custom-info='${JSON.stringify(customInfo)}'
                 data-original-name="${escapeHtml(displayName)}"
                 data-license="${escapeHtml(font.commercial_license)}">
                <div class="card-preview">
                    <img src="${previewUrl}" alt="${displayName}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'100\' height=\'100\' viewBox=\'0 0 100 100\'%3E%3Crect width=\'100\' height=\'100\' fill=\'%23e2e8f0\'/%3E%3Ctext x=\'50\' y=\'55\' text-anchor=\'middle\' fill=\'%23718096\' font-size=\'12\'%3E无预览图%3C/text%3E%3C/svg%3E'">
                </div>
                <div class="card-info">
                    <div class="card-title" title="${displayName}">${escapeHtml(displayName)}</div>
                    <div class="card-meta">
                        <span>📄 ${ext}</span>
                        <span class="license ${licenseClass}">${licenseText}</span>
                    </div>
                </div>
            </div>
        `;
    }
    grid.innerHTML = html;

    // 为每个卡片绑定单击跳转和双击编辑
    let clickTimer = null;
    document.querySelectorAll('.card').forEach(card => {
        // 单击跳转（延迟执行，避免双击时误跳转）
        card.addEventListener('click', (e) => {
            if (clickTimer) return;
            clickTimer = setTimeout(() => {
                const fontName = card.dataset.fontName;
                window.location.href = `/detail/${encodeURIComponent(fontName)}`;
                clickTimer = null;
            }, 200);
        });

        // 双击字体名编辑（取消单击跳转）
        const titleElem = card.querySelector('.card-title');
        if (titleElem) {
            titleElem.addEventListener('click', (e) => {
                e.stopPropagation();
                if (clickTimer) {
                    clearTimeout(clickTimer);
                    clickTimer = null;
                }
                const fontName = card.dataset.fontName;
                const customInfo = JSON.parse(card.dataset.customInfo || '{}');
                const license = card.dataset.license;
                checkAuthAndExecute(() => openEditModal(fontName, customInfo, license));
                openEditModal(fontName, customInfo, license);
            });
        }
    });
}

function showLoginModal(callback) {
    pendingAction = callback;
    loginModal.style.display = 'flex';
}

function closeLoginModal() {
    loginModal.style.display = 'none';
    pendingAction = null;
    document.getElementById('loginError').innerText = '';
}

// 登录表单提交
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    errorDiv.innerText = '';
    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            closeLoginModal();
            if (pendingAction) pendingAction();
            pendingAction = null;
            // 刷新当前页面数据
            if (document.getElementById('cardGrid')) loadFonts();
            if (document.getElementById('detailContent')) loadFontDetail();
        } else {
            errorDiv.innerText = data.error || '登录失败';
        }
    } catch (err) {
        errorDiv.innerText = '网络错误，请重试';
    }
});

if (closeLogin) closeLogin.onclick = closeLoginModal;
window.onclick = (event) => {
    if (event.target === loginModal) closeLoginModal();
};

// 检查认证并执行操作
async function checkAuthAndExecute(callback) {
    try {
        const res = await fetch('/api/check-auth');
        const data = await res.json();
        if (data.loggedIn) {
            callback();
        } else {
            showLoginModal(callback);
        }
    } catch (err) {
        console.error('认证检查失败', err);
        alert('无法验证登录状态，请重试');
    }
}

function renderPagination() {
    const container = document.getElementById('pagination');
    if (!container) return;
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let buttons = '';
    if (currentPage > 1) {
        buttons += `<button data-page="${currentPage-1}">← 上一页</button>`;
    }
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            buttons += `<button class="active" data-page="${i}">${i}</button>`;
        } else if (Math.abs(i - currentPage) <= 2 || i === 1 || i === totalPages) {
            buttons += `<button data-page="${i}">${i}</button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            buttons += `<button disabled>...</button>`;
        }
    }
    if (currentPage < totalPages) {
        buttons += `<button data-page="${currentPage+1}">下一页 →</button>`;
    }

    container.innerHTML = buttons;
    container.querySelectorAll('button[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage = parseInt(btn.dataset.page);
            loadFonts();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

function setupSearch() {
    const input = document.getElementById('searchInput');
    const btn = document.getElementById('searchBtn');
    if (!input || !btn) return;
    const search = () => {
        currentSearch = input.value.trim();
        currentPage = 1;
        loadFonts();
    };
    btn.addEventListener('click', search);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') search();
    });
}

// ==================== 详情页逻辑 ====================
function loadFontDetail() {
    if (typeof fontName !== 'undefined') {
        fetchFontDetail(fontName);
    } else {
        const pathParts = window.location.pathname.split('/');
        const name = decodeURIComponent(pathParts[pathParts.length - 1]);
        fetchFontDetail(name);
    }
}

function fetchFontDetail(fontName) {
    const container = document.getElementById('detailContent');
    if (!container) return;
    container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-pulse"></i> 加载中...</div>';

    fetch(`/api/font/${encodeURIComponent(fontName)}`)
        .then(res => {
            if (!res.ok) throw new Error('字体不存在');
            return res.json();
        })
        .then(data => renderDetail(data))
        .catch(err => {
            console.error(err);
            container.innerHTML = '<div class="loading">😢 字体详情加载失败</div>';
        });
}

function renderDetail(data) {
    const container = document.getElementById('detailContent');
    if (!container) return;

    // 语言映射
    const langOrder = ['简', '繁', '日', '韩', '英'];
    const supportedLangs = data.supported_languages || '';
    const availableLangs = langOrder.filter(lang => supportedLangs.includes(lang));
    const baseName = basenameWithoutExt(data.font_name);
    const previewUrls = availableLangs.map(lang =>
        `/preview/${encodeURIComponent(baseName)}_${lang}_preview.png`
    );

    let carouselHtml = '';
    if (availableLangs.length === 0) {
        carouselHtml = `<div class="carousel-container"><div class="carousel-images"><img src="/static/no_preview.png" alt="无预览图"></div></div>`;
    } else {
        carouselHtml = `
            <div class="carousel-container">
                <button class="carousel-prev" id="prevBtn">❮</button>
                <div class="carousel-images">
                    <img id="carouselImg" src="${previewUrls[0]}" alt="预览图">
                </div>
                <button class="carousel-next" id="nextBtn">❯</button>
            </div>
            <div class="carousel-dots" id="carouselDots"></div>
        `;
    }

    // name_records 表格
    let nameRecordsHtml = '';
    for (const [key, fields] of Object.entries(data.name_records)) {
        nameRecordsHtml += `
            <div class="record-group">
                <h4>${escapeHtml(key)}</h4>
                <table class="record-table">
                    ${Object.entries(fields).map(([field, value]) => `
                        <tr>
                            <td>${escapeHtml(field)}</td>
                            <td>${escapeHtml(value)}</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        `;
    }

    const licenseClass = data.final_license;
    let licenseDisplay = '';
    if (licenseClass === 'unknown') {
        licenseDisplay = '商用需授权';
    } else if (licenseClass && licenseClass.toLowerCase() === 'free') {
        licenseDisplay = '开源协议: 其他开源/免费声明';
    } else {
        licenseDisplay = `开源协议: ${licenseClass?.toUpperCase() || ''}`;
    }

    const downloadLink = data.download_link;
    const hasLink = downloadLink && downloadLink.trim() !== '';
    const linkHtml = hasLink
        ? `<a href="${downloadLink}" target="_blank" class="detail-meta-item">🔗 下载链接</a>`
        : `<span class="detail-meta-item disabled-link" data-tip="暂无下载链接，请根据字体名前往互联网搜索">🔗 下载链接</span>`;

    // 标题：优先自定义名称，否则使用数据库名去除扩展名
    let titleDisplay = data.custom_info?.custom_font_name || basenameWithoutExt(data.font_name);
    titleDisplay = titleDisplay.replace(/／/g, '|');

    const html = `
        <div class="detail-card">
            <div class="detail-preview">${carouselHtml}</div>
            <div class="detail-info">
                <h2>${escapeHtml(titleDisplay.replace(/／/g, '|'))}</h2>
                <div class="detail-meta">
                    <div class="detail-meta-item">📄 字符总数: ${data.total_characters}</div>
                    <div class="detail-meta-item license ${licenseClass}">🔒 ${licenseDisplay}</div>
                    <div class="detail-meta-item">🌐 支持语言: ${data.supported_languages || '无'}</div>
                    <div class="detail-meta-item">⚖️ 字重: ${data.font_weight}</div>
                    ${linkHtml}
                </div>
                <div class="name-records">
                    <h3>📋 字体元数据</h3>
                    ${nameRecordsHtml || '<p>无详细记录</p>'}
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;

    // 轮播图逻辑
    if (availableLangs.length > 0) {
        let currentIndex = 0;
        const imgElement = document.getElementById('carouselImg');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const dotsContainer = document.getElementById('carouselDots');

        if (dotsContainer) {
            dotsContainer.innerHTML = '';
            previewUrls.forEach((_, i) => {
                const dot = document.createElement('span');
                dot.classList.add('dot');
                if (i === currentIndex) dot.classList.add('active');
                dot.addEventListener('click', () => updateCarousel(i));
                dotsContainer.appendChild(dot);
            });
        }

        function updateCarousel(index) {
            currentIndex = (index + previewUrls.length) % previewUrls.length;
            if (imgElement) imgElement.src = previewUrls[currentIndex];
            document.querySelectorAll('.dot').forEach((dot, i) => {
                dot.classList.toggle('active', i === currentIndex);
            });
        }

        if (prevBtn) prevBtn.addEventListener('click', () => updateCarousel(currentIndex - 1));
        if (nextBtn) nextBtn.addEventListener('click', () => updateCarousel(currentIndex + 1));
    }

    // 保存当前详情页信息供双击编辑使用
    window.currentDetailFontName = data.font_name;
    window.currentDetailCustomInfo = data.custom_info || {};
    const fontNameElem = document.querySelector('.detail-info h2');
    if (fontNameElem) {
        fontNameElem.addEventListener('click', () => {
            checkAuthAndExecute(() => openEditModal(currentDetailFontName, currentDetailCustomInfo, data.final_license));
        });
    }
}

async function refreshDetailIfNeeded(fontName) {
    if (currentDetailFontName === fontName) {
        const url = `/api/font/${encodeURIComponent(fontName)}?_=${Date.now()}`;
        const response = await fetch(url);
        const data = await response.json();
        if (response.ok) {
            renderDetail(data);
        }
    }
}

// ==================== 编辑字体模态框 ====================
async function openEditModal(fontName, customInfo, currentLicense) {
    // 检查登录状态
    try {
        const res = await fetch('/api/check-auth');
        const data = await res.json();
        if (!data.loggedIn) {
            alert('请先登录');
            window.location.href = '/login';
            return;
        }
    } catch (err) {
        console.error('登录检查失败', err);
        alert('检查登录状态失败，请重试');
        return;
    }
    // 原有赋值代码...
    currentEditFontName = fontName;
    document.getElementById('editFontName').value = fontName;
    document.getElementById('customFontName').value = customInfo.custom_font_name || '';
    document.getElementById('customDownloadLink').value = customInfo.custom_download_link || '';
    document.getElementById('customFontWeight').value = customInfo.custom_font_weight || '';
    const licenseSelect = document.getElementById('customLicenseSelect');
    if (licenseSelect) licenseSelect.value = customInfo.custom_license || '';
    document.getElementById('editFontModal').style.display = 'flex';
}

function closeEditModal() {
    const modal = document.getElementById('editFontModal');
    if (modal) modal.style.display = 'none';
}

// 关闭按钮和背景点击
const closeModalBtn = document.querySelector('.close-modal');
if (closeModalBtn) closeModalBtn.addEventListener('click', closeEditModal);
const cancelBtn = document.getElementById('cancelEditBtn');
if (cancelBtn) cancelBtn.addEventListener('click', closeEditModal);
window.addEventListener('click', (event) => {
    const modal = document.getElementById('editFontModal');
    if (event.target === modal) closeEditModal();
});

// 保存编辑
const editForm = document.getElementById('editFontForm');
if (editForm) {
    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fontName = currentEditFontName;
        const customName = document.getElementById('customFontName').value.trim();
        const downloadLink = document.getElementById('customDownloadLink').value.trim();
        const fontWeight = document.getElementById('customFontWeight').value.trim();
        const customLicenseSelect = document.getElementById('customLicenseSelect');
        const customLicense = customLicenseSelect ? customLicenseSelect.value : '';

        if (!customName && !downloadLink && !fontWeight && !customLicense) {
            alert('请至少填写一项');
            return;
        }

        const data = {
            custom_font_name: customName,
            custom_download_link: downloadLink,
            custom_font_weight: fontWeight,
            custom_license: customLicense
        };
        if (customLicense !== '') {
            data.commercial_license = customLicense;
        }

        try {
            const response = await fetch(`/api/font/${encodeURIComponent(fontName)}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.status === 401) {
                alert('请先登录');
                window.location.href = '/login';
                return;
            }
            const result = await response.json();
            if (response.ok) {
                alert('保存成功');
                closeEditModal();
                // 刷新首页卡片（如果存在）
                if (document.getElementById('cardGrid')) {
                    updateCardInList(fontName, data, customLicense);
                }
                refreshDetailIfNeeded(fontName);
            }
        } catch (err) {
            alert('请求错误: ' + err.message);
        }
    });
}

// 重置按钮
const resetBtn = document.getElementById('resetEditBtn');
if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
        const fontName = currentEditFontName;
        const data = {
            custom_font_name: '',
            custom_download_link: '',
            custom_font_weight: '',
            custom_license: ''
        };
        try {
            const response = await fetch(`/api/font/${encodeURIComponent(fontName)}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (response.ok) {
                alert('已重置');
                closeEditModal();
                // 刷新首页卡片
                if (document.getElementById('cardGrid')) {
                    loadFonts(); // 或 updateCardInList...
                }
                refreshDetailIfNeeded(fontName);
            } else {
                alert('重置失败: ' + result.error);
            }
        } catch (err) {
            alert('请求错误: ' + err.message);
        }
    });
}

function updateCardInList(fontName, customInfo, newLicense) {
    const card = document.querySelector(`.card[data-font-name="${escapeHtml(fontName)}"]`);
    if (!card) return;
    // 更新 customInfo dataset
    card.dataset.customInfo = JSON.stringify(customInfo);
    if (newLicense !== undefined) {
        card.dataset.license = newLicense;
    }
    // 更新字体名显示
    const titleElem = card.querySelector('.card-title');
    if (titleElem) {
        let newDisplayName = customInfo.custom_font_name || card.dataset.originalName || fontName;
        titleElem.textContent = newDisplayName;
        titleElem.title = newDisplayName;
    }
    // 更新协议显示
    const licenseSpan = card.querySelector('.license');
    if (licenseSpan && newLicense !== undefined) {
        licenseSpan.textContent = newLicense.toUpperCase();
        // 更新 class：移除旧的协议类，添加新的
        const oldLicenseClass = licenseSpan.className.split(' ').find(c => c !== 'license');
        if (oldLicenseClass) licenseSpan.classList.remove(oldLicenseClass);
        licenseSpan.classList.add(newLicense);
    }
}

// ==================== 上传字体模态框（首页） ====================
const uploadModal = document.getElementById('uploadModal');
const uploadBtn = document.getElementById('uploadBtn');
const uploadClose = document.querySelector('#uploadModal .close');
const uploadTypeSelect = document.getElementById('uploadType');
const singleArea = document.getElementById('singleUploadArea');
const batchArea = document.getElementById('batchUploadArea');



if (uploadClose){
    uploadBtn.addEventListener('click', () => {
        checkAuthAndExecute(() => {
            // 打开上传模态框的代码
            uploadModal.style.display = 'block';
        });
    });
}
if (uploadClose) uploadClose.onclick = () => { if (uploadModal) uploadModal.style.display = 'none'; };
if (uploadModal) {
    window.onclick = (event) => {
        if (event.target === uploadModal) uploadModal.style.display = 'none';
    };
}
if (uploadTypeSelect) {
    uploadTypeSelect.addEventListener('change', function() {
        if (this.value === 'single') {
            if (singleArea) singleArea.style.display = 'block';
            if (batchArea) batchArea.style.display = 'none';
        } else {
            if (singleArea) singleArea.style.display = 'none';
            if (batchArea) batchArea.style.display = 'block';
        }
    });
}

const uploadForm = document.getElementById('uploadForm');
if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const uploadTypeVal = document.getElementById('uploadType').value;
        const formData = new FormData();
        const resultDiv = document.getElementById('uploadResult');
        resultDiv.innerHTML = '上传处理中，请稍候...';

        if (uploadTypeVal === 'single') {
            const fileInput = document.getElementById('singleFile');
            if (!fileInput.files.length) {
                alert('请选择字体文件');
                return;
            }
            formData.append('single_file', fileInput.files[0]);
            // 不再添加 mode 和 shape_name
        } else {
            const batchFiles = document.getElementById('batchFiles');
            if (!batchFiles.files.length) {
                alert('请选择至少一个字体文件');
                return;
            }
            for (let i = 0; i < batchFiles.files.length; i++) {
                formData.append('batch_files', batchFiles.files[i]);
            }
            // 批量上传也不添加 mode
        }

        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            if (response.status === 401) {
                alert('请先登录');
                window.location.href = '/login';
                return;
            }
            const data = await response.json();
            if (response.ok) {
                if (data.results) {
                    const successCount = data.results.filter(r => r.success).length;
                    resultDiv.innerHTML = `批量上传完成，成功 ${successCount} 个，失败 ${data.results.length - successCount} 个。`;
                } else {
                    resultDiv.innerHTML = '上传成功！正在刷新列表...';
                }
                // 重置分页和搜索条件
                currentPage = 1;
                currentSearch = '';
                const searchInput = document.getElementById('searchInput');
                if (searchInput) searchInput.value = '';
                loadFonts();  // 重新加载第一页
                // 关闭模态框并清空文件输入
                const modal = document.getElementById('uploadModal');
                if (modal) modal.style.display = 'none';
                const singleFile = document.getElementById('singleFile');
                if (singleFile) singleFile.value = '';
                const batchFiles = document.getElementById('batchFiles');
                if (batchFiles) batchFiles.value = '';
            } else {
                resultDiv.innerHTML = `上传失败: ${data.error}`;
            }
        } catch (err) {
            resultDiv.innerHTML = `请求错误: ${err.message}`;
        }
    });
}

// 加载预设蒙版列表（用于上传）
async function loadMaskPresets() {
    try {
        const res = await fetch('/api/mask-presets');
        const data = await res.json();
        const charSelect = document.getElementById('charSelect');
        if (charSelect) {
            data.characters.forEach(char => {
                const opt = document.createElement('option');
                opt.value = char;
                opt.textContent = char;
                charSelect.appendChild(opt);
            });
        }
        const imageSelect = document.getElementById('imageSelect');
        if (imageSelect) {
            data.images.forEach(img => {
                const opt = document.createElement('option');
                opt.value = img;
                opt.textContent = img;
                imageSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('加载预设蒙版失败:', err);
    }
}

// 词云生成器按钮
const wordcloudBtn = document.getElementById('wordcloudBtn');
if (wordcloudBtn) {
    wordcloudBtn.addEventListener('click', () => {
        window.location.href = '/wordcloud-generator';
    });
}

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    // 首页
    if (document.getElementById('cardGrid')) {
        loadFonts();
        setupSearch();
    }

    const cancelUploadBtn = document.getElementById('cancelUploadBtn');
    if (cancelUploadBtn) {
        cancelUploadBtn.addEventListener('click', () => {
            const modal = document.getElementById('uploadModal');
            if (modal) modal.style.display = 'none';
        });
    }

    // 详情页
    if (document.getElementById('detailContent')) {
        loadFontDetail();
    }
    // 上传模态框的额外逻辑（自定义字符/图片等）
    const charSelect = document.getElementById('charSelect');
    const imageSelect = document.getElementById('imageSelect');
    const customCharInputDiv = document.getElementById('customCharInputDiv');
    const customImageInputDiv = document.getElementById('customImageInputDiv');
    if (charSelect) {
        charSelect.addEventListener('change', () => {
            if (customCharInputDiv) customCharInputDiv.style.display = (charSelect.value === 'custom') ? 'block' : 'none';
        });
    }
    if (imageSelect) {
        imageSelect.addEventListener('change', () => {
            if (customImageInputDiv) customImageInputDiv.style.display = (imageSelect.value === 'custom') ? 'block' : 'none';
        });
    }
    // 加载预设蒙版
    loadMaskPresets();
});