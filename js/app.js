// ===== Navbar Scroll Effect =====
const navbar = document.getElementById('navbar');
if (navbar) {
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    });
}

// ===== Mobile Menu =====
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('open');
    });
    // Close menu on link click
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => navLinks.classList.remove('open'));
    });
}

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ===== Tab Switching =====
function initTabs() {
    document.querySelectorAll('.tabs').forEach(tabGroup => {
        const tabs = tabGroup.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.tab;
                // Deactivate all tabs
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                // Switch content
                const parent = tabGroup.parentElement;
                parent.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.toggle('active', content.id === target);
                });
            });
        });
    });
}
initTabs();

// ===== Bot Builder: Command Management =====
function addCommand() {
    const container = document.getElementById('commandsList');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'command-row';
    row.innerHTML = `
        <input type="text" placeholder="/command" class="cmd-input">
        <input type="text" placeholder="Bot response..." class="cmd-response">
        <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">X</button>
    `;
    container.appendChild(row);
}

function addAutoReply() {
    const container = document.getElementById('autoRepliesList');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'reply-row';
    row.innerHTML = `
        <input type="text" placeholder="Trigger keyword..." class="trigger-input">
        <input type="text" placeholder="Auto reply..." class="reply-input">
        <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">X</button>
    `;
    container.appendChild(row);
}

// ===== Bot Builder: Live Chat Preview =====
function initChatPreview() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const preview = document.getElementById('chatPreview');
    if (!input || !sendBtn || !preview) return;

    function addMessage(text, type) {
        const msg = document.createElement('div');
        msg.className = `msg ${type}`;
        msg.textContent = text;
        preview.appendChild(msg);
        preview.scrollTop = preview.scrollHeight;
    }

    function getBotResponse(userMsg) {
        const lower = userMsg.toLowerCase().trim();

        // Check commands
        const cmdInputs = document.querySelectorAll('.cmd-input');
        const cmdResponses = document.querySelectorAll('.cmd-response');
        for (let i = 0; i < cmdInputs.length; i++) {
            if (cmdInputs[i].value && lower === cmdInputs[i].value.toLowerCase()) {
                return cmdResponses[i].value || 'No response configured.';
            }
        }

        // Check auto-replies (keyword match)
        const triggers = document.querySelectorAll('.trigger-input');
        const replies = document.querySelectorAll('.reply-input');
        for (let i = 0; i < triggers.length; i++) {
            if (triggers[i].value && lower.includes(triggers[i].value.toLowerCase())) {
                return replies[i].value || 'No response configured.';
            }
        }

        // Check welcome message
        const welcomeMsg = document.getElementById('welcomeMessage');
        if (welcomeMsg && welcomeMsg.value && (lower === 'hi' || lower === 'hello' || lower === 'hey')) {
            return welcomeMsg.value;
        }

        return "I'm not configured to respond to that. Add a command or auto-reply!";
    }

    function sendMessage() {
        const text = input.value.trim();
        if (!text) return;
        addMessage(text, 'user');
        input.value = '';
        setTimeout(() => {
            addMessage(getBotResponse(text), 'bot');
        }, 400);
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Initial bot greeting
    setTimeout(() => addMessage('Hello! Try sending me a message to test your bot configuration.', 'bot'), 500);
}
initChatPreview();

// ===== Bot Builder: Export Config =====
function exportConfig() {
    const config = {
        botName: document.getElementById('botName')?.value || 'MyBot',
        welcomeMessage: document.getElementById('welcomeMessage')?.value || '',
        commands: [],
        autoReplies: [],
        scheduledMessages: [],
    };

    document.querySelectorAll('.command-row').forEach(row => {
        const cmd = row.querySelector('.cmd-input')?.value;
        const res = row.querySelector('.cmd-response')?.value;
        if (cmd) config.commands.push({ command: cmd, response: res || '' });
    });

    document.querySelectorAll('.reply-row').forEach(row => {
        const trigger = row.querySelector('.trigger-input')?.value;
        const reply = row.querySelector('.reply-input')?.value;
        if (trigger) config.autoReplies.push({ trigger, reply: reply || '' });
    });

    document.querySelectorAll('.schedule-row').forEach(row => {
        const msg = row.querySelector('.schedule-msg')?.value;
        const time = row.querySelector('.schedule-time')?.value;
        if (msg && time) config.scheduledMessages.push({ message: msg, time });
    });

    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.botName}_config.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// ===== Dashboard: Add Schedule Row =====
function addSchedule() {
    const container = document.getElementById('scheduleList');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'command-row schedule-row';
    row.innerHTML = `
        <input type="text" placeholder="Message to send..." class="schedule-msg">
        <input type="time" class="schedule-time">
        <button class="btn btn-danger btn-sm" onclick="this.parentElement.remove()">X</button>
    `;
    container.appendChild(row);
}

// ===== Animate elements on scroll =====
const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

document.querySelectorAll('.feature-card, .step, .pricing-card, .faq-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
});
