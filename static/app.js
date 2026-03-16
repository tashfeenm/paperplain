/* paperplain frontend */

const input = document.getElementById("paper-input");
const btn = document.getElementById("explain-btn");
const errorSection = document.getElementById("error-section");
const errorMessage = document.getElementById("error-message");
const loadingSection = document.getElementById("loading-section");
const loadingStatus = document.getElementById("loading-status");
const resultSection = document.getElementById("result-section");

// Allow Enter key to trigger explain
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !btn.disabled) {
        explainPaper();
    }
});

// Load recent papers on page load
document.addEventListener("DOMContentLoaded", loadRecent);

function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = "block";
    loadingSection.style.display = "none";
    resultSection.style.display = "none";
}

function hideError() {
    errorSection.style.display = "none";
}

function showLoading(status) {
    loadingStatus.textContent = status;
    loadingSection.style.display = "block";
    resultSection.style.display = "none";
    hideError();
}

function hideLoading() {
    loadingSection.style.display = "none";
}

function setButtonLoading(loading) {
    btn.disabled = loading;
    btn.textContent = loading ? "Processing..." : "Explain this paper";
}

function textToHtml(text) {
    // Split on double newlines to create paragraphs
    const paragraphs = text.split(/\n\n+/).filter((p) => p.trim());
    return paragraphs.map((p) => `<p>${escapeHtml(p.trim())}</p>`).join("");
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

async function explainPaper() {
    const url = input.value.trim();
    if (!url) {
        showError("Please enter an arxiv URL or paper ID.");
        return;
    }

    hideError();
    setButtonLoading(true);
    showLoading("Fetching metadata from arxiv...");

    // Cycle through loading messages
    const messages = [
        "Fetching metadata from arxiv...",
        "Downloading PDF...",
        "Converting PDF to text with Docling...",
        "Sending to Claude for explanation...",
        "Almost there, generating your explanation...",
    ];
    let msgIndex = 0;
    const loadingInterval = setInterval(() => {
        msgIndex++;
        if (msgIndex < messages.length) {
            loadingStatus.textContent = messages[msgIndex];
        }
    }, 8000);

    try {
        const response = await fetch("/api/explain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        clearInterval(loadingInterval);

        if (!response.ok) {
            const data = await response.json().catch(() => null);
            const detail = data?.detail || `Server error (${response.status})`;
            showError(detail);
            setButtonLoading(false);
            return;
        }

        const paper = await response.json();
        renderPaper(paper);
        loadRecent(); // Refresh the recent list
    } catch (err) {
        clearInterval(loadingInterval);
        showError(
            "Could not connect to the server. Make sure it is running."
        );
    }

    setButtonLoading(false);
}

function renderPaper(paper) {
    hideLoading();
    hideError();

    document.getElementById("paper-title").textContent = paper.title;
    document.getElementById("paper-authors").textContent =
        paper.authors.join(", ");

    const link = document.getElementById("paper-link");
    link.href = paper.arxiv_url;
    link.textContent = `View original paper on arxiv (${paper.arxiv_id})`;

    document.getElementById("explanation-tldr").innerHTML = textToHtml(
        paper.explanation.tldr
    );
    document.getElementById("explanation-idea").innerHTML = textToHtml(
        paper.explanation.the_idea
    );
    document.getElementById("explanation-matters").innerHTML = textToHtml(
        paper.explanation.why_it_matters
    );
    document.getElementById("explanation-missing").innerHTML = textToHtml(
        paper.explanation.whats_missing
    );

    resultSection.style.display = "block";

    // Scroll to result
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadRecent() {
    const recentList = document.getElementById("recent-list");

    try {
        const response = await fetch("/api/recent");
        if (!response.ok) return;

        const papers = await response.json();

        if (papers.length === 0) {
            recentList.innerHTML =
                '<li class="recent-empty">No papers explained yet. Try one above!</li>';
            return;
        }

        recentList.innerHTML = papers
            .map(
                (p) => `
            <li>
                <a href="javascript:void(0)" onclick="loadPaper('${escapeHtml(p.arxiv_id)}')">
                    <span class="recent-title">${escapeHtml(p.title)}</span>
                    <span class="recent-id">${escapeHtml(p.arxiv_id)}</span>
                </a>
            </li>
        `
            )
            .join("");
    } catch {
        // Silently fail — recent list is not critical
    }
}

async function loadPaper(arxivId) {
    hideError();
    setButtonLoading(true);
    showLoading("Loading cached explanation...");

    try {
        const response = await fetch(`/api/paper/${arxivId}`);
        if (!response.ok) {
            const data = await response.json().catch(() => null);
            showError(data?.detail || "Failed to load paper.");
            setButtonLoading(false);
            return;
        }

        const paper = await response.json();
        input.value = arxivId;
        renderPaper(paper);
    } catch {
        showError("Could not connect to the server.");
    }

    setButtonLoading(false);
}
