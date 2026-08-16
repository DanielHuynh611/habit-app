(() => {
  "use strict";

  const TOKEN_KEY = "zorentia_access_token";
  const PUBLIC_PATHS = new Set(["/login", "/signup"]);
  const path = window.location.pathname.replace(/\/$/, "") || "/";

  const escapeHtml = (value) => String(value ?? "").replace(
    /[&<>'"]/g,
    (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    })[character],
  );

  const token = () => window.localStorage.getItem(TOKEN_KEY);

  const safeNextPath = () => {
    const requested = new URLSearchParams(window.location.search).get("next");
    return requested && requested.startsWith("/") && !requested.startsWith("//")
      ? requested
      : "/habits";
  };

  const todayIso = () => {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };

  const formatDate = (value, options = {}) => {
    if (!value) return "Never";
    const dateValue = String(value).slice(0, 10);
    const parsed = new Date(`${dateValue}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleDateString(undefined, {
      year: "numeric",
      month: options.long ? "long" : "short",
      day: "numeric",
    });
  };

  const formatDateTime = (value) => {
    if (!value) return "Not completed yet";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime())
      ? String(value)
      : parsed.toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        });
  };

  const addStylesheet = () => {
    if (document.querySelector('link[href="/static/css/app.css"]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/static/css/app.css";
    document.head.append(link);
  };

  const showNotice = (message, type = "error") => {
    document.querySelector("[data-app-notice]")?.remove();
    const main = document.querySelector("#main-content") || document.body;
    const notice = document.createElement("div");
    notice.dataset.appNotice = "true";
    notice.className = `app-notice app-notice-${type}`;
    notice.setAttribute("role", type === "error" ? "alert" : "status");
    notice.textContent = message;
    main.prepend(notice);
    notice.scrollIntoView({ block: "nearest" });
  };

  const setBusy = (root, busy) => {
    root?.setAttribute("aria-busy", String(busy));
    root?.querySelectorAll("button, input, select, textarea").forEach((node) => {
      node.disabled = busy;
    });
  };

  const api = async (url, { method = "GET", body, auth = true } = {}) => {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && token()) headers.Authorization = `Bearer ${token()}`;

    let response;
    try {
      response = await window.fetch(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (_error) {
      throw new Error("Cannot reach the server. Confirm the app and MySQL are running.");
    }

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && auth) {
        window.localStorage.removeItem(TOKEN_KEY);
      }
      throw new Error(
        payload.message || payload.error || `Request failed (${response.status})`,
      );
    }
    return payload;
  };

  const setupNavigation = () => {
    document.querySelectorAll('a[href="' + path + '"]').forEach((link) => {
      link.setAttribute("aria-current", "page");
    });

    document.querySelectorAll(".menu-toggle").forEach((button) => {
      button.setAttribute("aria-expanded", "false");
      button.addEventListener("click", () => {
        const shell = document.querySelector(".app-shell");
        const isOpen = shell?.classList.toggle("sidebar-open") || false;
        button.setAttribute("aria-expanded", String(isOpen));
      });
    });

    if (!token() || PUBLIC_PATHS.has(path)) return;
    document.querySelectorAll('a[href="/login"]').forEach((link) => {
      link.href = "#logout";
      const label = link.querySelector("span:last-child");
      if (label) label.textContent = "Log Out";
      else link.textContent = "Log Out";
      link.addEventListener("click", (event) => {
        event.preventDefault();
        window.localStorage.removeItem(TOKEN_KEY);
        window.location.assign("/login");
      });
    });
    document.querySelectorAll('a[href="/signup"]').forEach((link) => {
      link.closest("li")?.setAttribute("hidden", "");
    });
  };

  const requireSession = () => {
    if (PUBLIC_PATHS.has(path) || token()) return true;
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace(`/login?next=${next}`);
    return false;
  };

  const handleFailure = (error) => {
    showNotice(error?.message || "Something went wrong. Please try again.");
    if (!token() && !PUBLIC_PATHS.has(path)) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.setTimeout(() => window.location.replace(`/login?next=${next}`), 700);
    }
  };

  const setupAuthForm = (mode) => {
    const form = document.querySelector("form[data-action-id]");
    if (!form) return;
    if (token()) {
      api("/api/auth/verify")
        .then(() => window.location.replace(safeNextPath()))
        .catch(() => window.localStorage.removeItem(TOKEN_KEY));
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const values = Object.fromEntries(new FormData(form).entries());
      setBusy(form, true);
      try {
        const payload = await api(
          mode === "login" ? "/api/auth/login" : "/api/auth/signup",
          { method: "POST", body: values, auth: false },
        );
        window.localStorage.setItem(TOKEN_KEY, payload.token);
        window.location.assign(safeNextPath());
      } catch (error) {
        handleFailure(error);
      } finally {
        setBusy(form, false);
      }
    });
  };

  const setupCreateHabit = () => {
    const form = document.querySelector("form[data-action-id]");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const name = String(new FormData(form).get("name") || "").trim();
      if (!name) {
        showNotice("Please enter a habit name.");
        return;
      }
      setBusy(form, true);
      try {
        await api("/api/habits", { method: "POST", body: { name } });
        window.location.assign("/habits?created=1");
      } catch (error) {
        handleFailure(error);
      } finally {
        setBusy(form, false);
      }
    });
  };

  const habitCard = (habit) => `
    <article class="panel habit-card">
      <div class="habit-card-main">
        <div class="habit-card-icon" aria-hidden="true">✓</div>
        <div>
          <h2 class="panel-title">${escapeHtml(habit.name)}</h2>
          <p class="panel-copy">Created ${escapeHtml(formatDate(habit.created_at))}</p>
        </div>
      </div>
      <div class="habit-card-actions">
        <a class="button button-primary" href="/habits/${encodeURIComponent(habit.id)}">
          View progress
        </a>
        <a class="button button-secondary" href="/habits/${encodeURIComponent(habit.id)}/heatmap">
          Heatmap
        </a>
      </div>
    </article>`;

  const loadHabitsPage = async () => {
    const section = document.querySelector(
      '[data-action-id*="load_habits"][data-autoload="true"]',
    );
    if (!section) return;
    try {
      const { habits } = await api("/api/habits");
      section.innerHTML = habits.length
        ? `<div class="card-grid">${habits.map(habitCard).join("")}</div>`
        : `<div class="empty-state">
             <div>
               <h2>No habits yet</h2>
               <p>Create your first habit to start tracking your progress.</p>
               <a href="/habits/new" class="button button-primary">Create your first habit</a>
             </div>
           </div>`;
      if (new URLSearchParams(window.location.search).has("created")) {
        showNotice("Habit created successfully.", "success");
      }
      const actions = document.querySelector(".page-header .actions");
      if (actions && !actions.querySelector('[href="/streaks"]')) {
        actions.insertAdjacentHTML(
          "afterbegin",
          '<a href="/streaks" class="button button-secondary">View streaks</a>',
        );
      }
    } catch (error) {
      handleFailure(error);
    }
  };

  const renderToday = (section, habits, completions, dateValue) => {
    const completionByHabit = new Map(
      completions.map((completion) => [completion.habit_id, completion]),
    );
    const items = habits.map((habit) => ({
      habit,
      completion: completionByHabit.get(habit.id),
      completed: Boolean(completionByHabit.get(habit.id)?.is_completed),
    }));
    const completedCount = items.filter((item) => item.completed).length;
    const percentage = items.length
      ? Math.round((completedCount / items.length) * 100)
      : 0;
    const rows = items.map(({ habit, completion, completed }) => `
      <div class="today-row" data-habit-id="${escapeHtml(habit.id)}">
        <label class="today-toggle">
          <input type="checkbox" ${completed ? "checked" : ""}
                 aria-label="Mark ${escapeHtml(habit.name)} complete">
          <span class="today-check" aria-hidden="true">✓</span>
          <span>
            <strong>${escapeHtml(habit.name)}</strong>
            <small>${completion ? `Updated ${escapeHtml(formatDateTime(completion.updated_at))}` : "Not checked today"}</small>
          </span>
        </label>
        <span class="badge">${completed ? "Done" : "Pending"}</span>
      </div>`).join("");

    section.innerHTML = `
      <div class="panel today-panel">
        <div class="today-summary">
          <h2 class="panel-title">${escapeHtml(formatDate(dateValue, { long: true }))}</h2>
          <span class="badge">${completedCount} / ${items.length} complete</span>
        </div>
        ${items.length ? `<div>${rows}</div>` : `
          <div class="empty-state">
            <div><h3>No habits yet</h3><p>Create a habit before tracking today.</p>
            <a class="button button-primary" href="/habits/new">Create a habit</a></div>
          </div>`}
      </div>
      <div class="stats-grid today-stats">
        <div class="stat"><div class="stat-label">Completion rate</div><div class="stat-value">${percentage}%</div></div>
        <div class="stat"><div class="stat-label">Completed today</div><div class="stat-value">${completedCount}</div></div>
        <div class="stat"><div class="stat-label">Total habits</div><div class="stat-value">${items.length}</div></div>
        <div class="stat"><div class="stat-label">Remaining</div><div class="stat-value">${items.length - completedCount}</div></div>
      </div>`;

    section.querySelectorAll(".today-row input[type='checkbox']").forEach((input) => {
      input.addEventListener("change", async () => {
        const row = input.closest(".today-row");
        input.disabled = true;
        try {
          await api(`/api/habits/${encodeURIComponent(row.dataset.habitId)}/completions`, {
            method: "PUT",
            body: { completion_date: dateValue, is_completed: input.checked },
          });
          await loadTodayPage();
        } catch (error) {
          input.checked = !input.checked;
          input.disabled = false;
          handleFailure(error);
        }
      });
    });
  };

  const loadTodayPage = async () => {
    const section = document.querySelector(
      '[data-action-id*="load_today_completions"][data-autoload="true"]',
    );
    if (!section) return;
    try {
      const [{ habits }, today] = await Promise.all([
        api("/api/habits"),
        api("/api/completions/today"),
      ]);
      renderToday(section, habits, today.completions, today.date || todayIso());
    } catch (error) {
      handleFailure(error);
    }
  };

  const rateStatus = (rate) => {
    if (rate >= 80) return "Excellent";
    if (rate >= 50) return "Good progress";
    if (rate > 0) return "Keep going";
    return "Ready to start";
  };

  const loadDashboard = async () => {
    const section = document.querySelector(
      '[data-action-id*="load_all_completion_rates"][data-autoload="true"]',
    );
    if (!section) return;
    try {
      const [{ completion_rates: rates }, { habits }] = await Promise.all([
        api("/api/habits/completion-rates"),
        api("/api/habits"),
      ]);
      const names = new Map(habits.map((habit) => [habit.id, habit.name]));
      section.innerHTML = rates.length
        ? `<div class="card-grid">${rates.map((rate) => `
            <article class="data-card rate-card">
              <div class="rate-heading">
                <div><h2 class="panel-title">${escapeHtml(names.get(rate.habit_id) || "Habit")}</h2>
                <p class="panel-copy">${rate.completed_days} of ${rate.total_days} days completed</p></div>
                <strong>${rate.completion_rate}%</strong>
              </div>
              <div class="progress-track"><span style="width:${Math.max(0, Math.min(100, rate.completion_rate))}%"></span></div>
              <div class="rate-footer"><span class="badge">${rateStatus(rate.completion_rate)}</span>
                <a href="/habits/${encodeURIComponent(rate.habit_id)}">View details →</a></div>
            </article>`).join("")}</div>`
        : `<div class="empty-state"><div><h3>No habits yet</h3>
             <p>Create a habit to start seeing statistics.</p>
             <a class="button button-primary" href="/habits/new">Create a habit</a></div></div>`;
    } catch (error) {
      handleFailure(error);
    }
  };

  const bindText = (name, value) => {
    document.querySelectorAll(`[data-bind="${name}"]`).forEach((node) => {
      node.textContent = value ?? "—";
    });
  };

  const habitIdFromPath = (suffix = "") => {
    const expression = suffix
      ? new RegExp(`^/habits/([^/]+)/${suffix}$`)
      : /^\/habits\/([^/]+)$/;
    const match = path.match(expression);
    return match ? decodeURIComponent(match[1]) : null;
  };

  const loadHabitDetail = async () => {
    const habitId = habitIdFromPath();
    if (!habitId) return;
    try {
      const [rate, streak, { habits }] = await Promise.all([
        api(`/api/habits/${encodeURIComponent(habitId)}/completion-rate`),
        api(`/api/habits/${encodeURIComponent(habitId)}/streak`),
        api("/api/habits"),
      ]);
      const habit = habits.find((item) => item.id === habitId);
      bindText("habit_name", habit?.name || "Habit progress");
      bindText("completion_rate", rate.completion_rate);
      bindText("completed_days", rate.completed_days);
      bindText("total_days", rate.total_days);
      document.querySelectorAll('[data-bind-attr="stroke-dashoffset"]').forEach((node) => {
        node.setAttribute(
          "stroke-dashoffset",
          String(502.4 - (502.4 * rate.completion_rate) / 100),
        );
      });
      const grid = document.querySelector(".panel-grid");
      if (grid) {
        grid.insertAdjacentHTML("afterbegin", `
          <section class="panel streak-overview">
            <h2 class="panel-title">Current streak</h2>
            <div class="streak-number">${streak.current_streak}</div>
            <p class="panel-copy">${streak.current_streak === 1 ? "day" : "days"} in a row</p>
            <p class="panel-copy">Last completed: ${escapeHtml(formatDate(streak.last_completion_date))}</p>
          </section>`);
      }
      const header = document.querySelector(".page-header");
      header?.insertAdjacentHTML("beforeend", `
        <div class="actions detail-actions">
          <a class="button button-secondary" href="/habits/${encodeURIComponent(habitId)}/streak">Streak details</a>
          <a class="button button-primary" href="/habits/${encodeURIComponent(habitId)}/heatmap">View heatmap</a>
        </div>`);
    } catch (error) {
      handleFailure(error);
    }
  };

  const loadStreakDetail = async () => {
    const habitId = habitIdFromPath("streak");
    if (!habitId) return;
    try {
      const [streak, { habits }] = await Promise.all([
        api(`/api/habits/${encodeURIComponent(habitId)}/streak`),
        api("/api/habits"),
      ]);
      const habit = habits.find((item) => item.id === habitId);
      bindText("habit_id", habit?.name || habitId);
      bindText("current_streak", streak.current_streak);
      bindText("last_completion_date", formatDate(streak.last_completion_date));
      document.querySelectorAll('[data-bind-if-gt="0"]').forEach((node) => {
        node.hidden = streak.current_streak <= 0;
      });
      document.querySelectorAll('[data-bind-if-eq="0"]').forEach((node) => {
        node.hidden = streak.current_streak !== 0;
      });
      document.querySelectorAll('[data-bind-show="last_completion_date"]').forEach((node) => {
        node.hidden = !streak.last_completion_date;
      });
      document.querySelectorAll('[data-bind-plural="current_streak"]').forEach((node) => {
        node.textContent = streak.current_streak === 1
          ? node.dataset.singular || "day"
          : node.dataset.plural || "days";
      });
    } catch (error) {
      handleFailure(error);
    }
  };

  const loadStreaks = async () => {
    const root = document.querySelector(
      '[data-action-id*="load_all_habits_streaks"][data-autoload="true"]',
    );
    if (!root) return;
    try {
      const [{ streaks }, { habits }] = await Promise.all([
        api("/api/habits/streaks"),
        api("/api/habits"),
      ]);
      const names = new Map(habits.map((habit) => [habit.id, habit.name]));
      root.innerHTML = streaks.length
        ? `<div class="streak-list">${streaks.map((streak) => `
            <a class="today-row" href="/habits/${encodeURIComponent(streak.habit_id)}/streak">
              <span><strong>${escapeHtml(names.get(streak.habit_id) || "Habit")}</strong>
              <small>Last completed: ${escapeHtml(formatDate(streak.last_completion_date))}</small></span>
              <span class="badge">🔥 ${streak.current_streak} ${streak.current_streak === 1 ? "day" : "days"}</span>
            </a>`).join("")}</div>`
        : `<div class="empty-state"><div><h3>No habits yet</h3><p>Create a habit to start a streak.</p>
             <a class="button button-primary" href="/habits/new">Create a habit</a></div></div>`;
    } catch (error) {
      handleFailure(error);
    }
  };

  const renderHeatmap = (days) => {
    const container = document.getElementById("heatmap-grid");
    if (!container) return;
    container.className = "heatmap-grid";
    container.innerHTML = days.map((day) => {
      const state = day.is_future ? "future" : day.completed ? "completed" : "missed";
      const label = `${formatDate(day.date)}: ${state}`;
      return `<span class="heatmap-day heatmap-day-${state}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"></span>`;
    }).join("");
  };

  const loadHeatmap = async () => {
    const habitId = habitIdFromPath("heatmap");
    if (!habitId) return;
    try {
      const payload = await api(`/api/habits/${encodeURIComponent(habitId)}/heatmap`);
      bindText("habit_name", payload.habit_name);
      bindText("current_streak", payload.current_streak);
      bindText("start_date", formatDate(payload.start_date));
      bindText("end_date", formatDate(payload.end_date));
      document.querySelectorAll('[data-bind="completion_rate"]').forEach((node) => {
        node.textContent = `${payload.completion_rate}%`;
      });
      renderHeatmap(payload.days);
      document.querySelector(".page-header")?.insertAdjacentHTML(
        "afterbegin",
        `<div class="page-kicker"><a href="/habits/${encodeURIComponent(habitId)}">← Back to habit</a></div>`,
      );
    } catch (error) {
      handleFailure(error);
    }
  };

  const start = () => {
    addStylesheet();
    setupNavigation();
    if (!requireSession()) return;

    if (path === "/login") setupAuthForm("login");
    else if (path === "/signup") setupAuthForm("signup");
    else if (path === "/habits/new") setupCreateHabit();
    else if (path === "/habits") loadHabitsPage();
    else if (path === "/habits/today") loadTodayPage();
    else if (path === "/dashboard") loadDashboard();
    else if (path === "/streaks") loadStreaks();
    else if (/^\/habits\/[^/]+\/heatmap$/.test(path)) loadHeatmap();
    else if (/^\/habits\/[^/]+\/streak$/.test(path)) loadStreakDetail();
    else if (/^\/habits\/[^/]+$/.test(path)) loadHabitDetail();
  };

  start();
})();
