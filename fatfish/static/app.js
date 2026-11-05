"use strict";
const $ = (id) => document.getElementById(id);
let token = "",
  state = null,
  populated = false,
  messageSignature = "",
  jobSignature = "",
  toastTimer;
let petPrefsPending = 0,
  petSave = Promise.resolve(),
  seenPetJobs = null,
  petVersion = 0,
  chatBusy = false,
  deepseekBusy = false;
const pet = new FishSprite($("pet-canvas"));
window.fish = pet;
pet.ready.catch((e) => toast(e.message));
const labels = {
  home: "我的鱼缸",
  explore: "出去逛逛",
  channels: "连接聊天账号",
  phone: "手机看视频",
  settings: "给小鱼装大脑",
  character: "形象与来源",
};
function tab(id) {
  document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== id));
  document
    .querySelectorAll(".nav")
    .forEach((n) => n.classList.toggle("active", n.dataset.tab === id));
  $("breadcrumb").textContent = labels[id];
  location.hash = id;
}
document
  .querySelectorAll("[data-tab],[data-go]")
  .forEach((b) =>
    b.addEventListener("click", () => tab(b.dataset.tab || b.dataset.go)),
  );
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 7000);
}
function result(id, message, error = false) {
  $(id).textContent = message;
  $(id).classList.toggle("error", error);
}
async function api(path, data) {
  const options =
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Fish-Token": token,
          },
          body: JSON.stringify(data),
        };
  const r = await fetch("/api/" + path, options);
  const d = await r.json();
  if (!r.ok) throw Error(d.error || "操作失败");
  return d;
}
function badge(id, text, ok) {
  $(id).textContent = text;
  $(id).className =
    "badge" + (ok === true ? " good" : ok === false ? " bad" : "");
}
function showCheck(id, check, configured) {
  badge(
    id,
    check
      ? check.ok
        ? "连接已验证"
        : "检测失败"
      : configured
        ? "已填写 · 待检测"
        : "未配置",
    check ? !!check.ok : null,
  );
}
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
function renderMessages(messages) {
  const signature = JSON.stringify(messages);
  if (signature === messageSignature) return;
  messageSignature = signature;
  const box = $("messages");
  box.replaceChildren();
  if (!messages.length)
    messages = [
      {
        role: "assistant",
        content:
          "你来啦！我刚刚只是闭目养神，才没有偷懒。\n要不要先喂我一碗白饭？",
      },
    ];
  messages.forEach((m) => {
    const row = el("div", "message " + (m.role === "user" ? "user" : ""));
    const avatar =
      m.role === "user"
        ? el("span", "avatar user-avatar", "你")
        : el("img", "avatar");
    if (m.role !== "user") {
      avatar.src = "/character.png";
      avatar.alt = "大肥鱼";
    }
    const body = el("div", "message-body");
    body.append(
      el(
        "span",
        "message-name",
        m.role === "user"
          ? "你"
          : m.mode === "demo"
            ? "大肥鱼 · 预设"
            : "大肥鱼",
      ),
      el("div", "message-text", m.content),
    );
    row.append(avatar, body);
    box.append(row);
  });
  box.scrollTop = box.scrollHeight;
}
function renderJobs(jobs) {
  const signature = JSON.stringify(jobs);
  if (signature === jobSignature) return;
  jobSignature = signature;
  const box = $("jobs");
  box.replaceChildren();
  if (!jobs.length) {
    const empty = el("div", "empty");
    empty.append(
      el("span", "", "≈"),
      document.createTextNode("还没出过门。给她安排一次小探索吧。"),
    );
    box.append(empty);
  }
  const statuses = {
    queued: "等待中",
    running: "进行中",
    done: "已完成",
    failed: "未成功",
    cancelled: "已停止",
    interrupted: "重启后已中断",
  };
  const kinds = {
    read: "读取网页",
    agent: "自主探索",
    video: "网页视频",
    phone: "手机浏览",
  };
  jobs.forEach((job) => {
    const card = el("article", "job"),
      head = el("div", "job-head");
    head.append(
      el("h3", "", kinds[job.kind] || job.kind),
      el(
        "span",
        "badge" +
          (job.status === "done"
            ? " good"
            : job.status === "failed"
              ? " bad"
              : ""),
        statuses[job.status] || job.status,
      ),
    );
    card.append(head);
    card.append(
      el("p", "job-url", job.body.args.url || job.body.args.package || ""),
    );
    if (job.body.summary)
      card.append(el("div", "job-summary", job.body.summary));
    const steps = el("details");
    steps.append(el("summary", "", `执行记录 · ${job.body.steps.length} 条`));
    job.body.steps.forEach((s) =>
      steps.append(el("div", "job-step", s.time + "　" + s.message)),
    );
    card.append(steps);
    if (
      job.body.artifact &&
      /^\/artifacts\/[a-f0-9]+\.png$/.test(job.body.artifact)
    ) {
      const link = el("a");
      link.href = job.body.artifact;
      link.target = "_blank";
      link.rel = "noopener";
      const img = el("img", "job-shot");
      img.src = job.body.artifact;
      img.alt = "任务执行后截图";
      img.loading = "lazy";
      link.append(img);
      card.append(link);
    }
    if (["queued", "running"].includes(job.status)) {
      const stop = el("button", "text-button danger", "停止这个任务");
      stop.addEventListener("click", async () => {
        try {
          await api("tasks/cancel", { id: job.id });
          toast("已发出停止请求");
          await refresh();
        } catch (e) {
          toast(e.message);
        }
      });
      card.append(stop);
    }
    box.append(card);
  });
}
function populate(s) {
  $("engine").value = s.engine;
  $("base-url").value = s.base_url;
  $("model").value = s.model;
  $("personality").value = s.personality;
  $("browser-steps").value = s.browser_steps;
  $("provider").value = s.base_url.includes("deepseek")
    ? "deepseek"
    : s.base_url.startsWith("http://127.0.0.1")
      ? "local"
      : "custom";
  $("onebot-url").value = s.onebot_url;
  $("qq-users").value = s.qq_users;
  $("qq-groups").value = s.qq_groups;
  $("qq-auto").checked = s.qq_auto;
  for (const [id, key] of [
    ["model-key", "model_key"],
    ["onebot-token", "onebot_token"],
    ["wecom-webhook", "wecom_webhook"],
  ])
    if (s[key + "_set"]) $(id).placeholder = "已保存 · 留空保留";
}
async function refresh() {
  const requestPetVersion = petVersion;
  const d = await api("state");
  state = d;
  await pet.ready;
  if (!petPrefsPending && requestPetVersion === petVersion) {
    pet.setForm(d.config.pet_form || "chibi");
    pet.setMotion(d.config.pet_motion !== false);
  }
  const done = new Set(
    d.jobs
      .filter((j) => ["done", "failed", "cancelled"].includes(j.status))
      .map((j) => j.id),
  );
  if (
    seenPetJobs &&
    [...done].some((id) => !seenPetJobs.has(id)) &&
    pet.action !== "sleep"
  )
    pet.play("jump");
  seenPetJobs = done;
  if (
    d.jobs.some((j) => ["running", "queued"].includes(j.status)) &&
    pet.action === "idle"
  )
    pet.play("work");
  else if (
    !d.jobs.some((j) => ["running", "queued"].includes(j.status)) &&
    pet.action === "work"
  )
    pet.play("idle");
  if (!populated) {
    populate(d.config);
    populated = true;
  }
  for (const [id, key] of [
    ["model-key", "model_key"],
    ["onebot-token", "onebot_token"],
    ["wecom-webhook", "wecom_webhook"],
  ])
    if (d.config[key + "_set"]) $(id).placeholder = "已保存 · 留空保留";
  const real = d.config.engine === "model";
  badge(
    "mode-badge",
    real
      ? d.checks.model?.ok
        ? "真实 AI · 已连接"
        : "真实 AI · 待检测"
      : "互动体验 · 预设回应",
    real && d.checks.model?.ok ? true : null,
  );
  $("chat-notice").textContent = real
    ? "真实 AI · 对话将发给你配置的模型服务"
    : "互动体验 · 当前为预设回应，未调用 AI";
  $("chat-notice").classList.toggle("real", real);
  showCheck("model-badge", d.checks.model, d.config.model_key_set);
  showCheck("qq-badge", d.checks.qq, !!d.config.onebot_url);
  showCheck("wechat-badge", d.checks.wechat, d.config.wecom_webhook_set);
  badge(
    "browser-badge",
    d.browser_installed ? "浏览组件已安装" : "需要安装浏览组件",
    d.browser_installed ? null : false,
  );
  $("step-budget").textContent = d.config.browser_steps;
  renderMessages(d.messages);
  renderJobs(d.jobs);
}
async function action(button, outId, fn) {
  button.disabled = true;
  result(outId, "正在处理……");
  try {
    const message = await fn();
    result(outId, message === undefined ? "已保存" : message);
    await refresh();
  } catch (e) {
    result(outId, e.message, true);
  } finally {
    button.disabled = false;
  }
}
$("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (chatBusy) return;
  const text = $("message").value.trim();
  if (!text) return;
  chatBusy = true;
  $("typing").hidden = false;
  $("clear-chat").disabled = true;
  try {
    await action($("chat-submit"), "chat-result", async () => {
      pet.play("think");
      try {
        await api("chat", { message: text });
        pet.play("wave");
      } catch (e) {
        pet.play("failed");
        throw e;
      }
      if ($("message").value.trim() === text) $("message").value = "";
      return "";
    });
  } finally {
    chatBusy = false;
    $("typing").hidden = true;
    $("clear-chat").disabled = false;
  }
});
$("message").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    if (!chatBusy) $("chat-form").requestSubmit();
  }
});
document.querySelectorAll("[data-prompt]").forEach((b) =>
  b.addEventListener("click", () => {
    $("message").value = b.dataset.prompt;
    $("message").focus();
  }),
);
let feeds = Number(localStorage.getItem("fish-feeds") || 0);
if (!Number.isFinite(feeds)) feeds = 0;
$("feed-count").textContent = feeds;
$("feed").addEventListener("click", () => {
  pet.play("feed");
  feeds++;
  localStorage.setItem("fish-feeds", String(feeds));
  $("feed-count").textContent = feeds;
  $("pet-speech").textContent = "白饭！\n好吧，今天你最好。🍚";
  $("pet-mood").textContent = "✦ 心满意足";
  toast("已投喂一碗白饭 · 本机小互动");
});
$("pet-touch").addEventListener("click", () => {
  pet.play("wave");
  $("pet-speech").textContent = [
    "我在认真思考！\n真的没有摸鱼。",
    "鲸鱼也是需要休息的。",
    "今天想去哪里逛逛？",
    "才不是大肥鱼，哼。",
  ][Math.floor(Math.random() * 4)];
});
function modelValues() {
  return {
    engine: $("engine").value,
    base_url: $("base-url").value,
    model: $("model").value,
    model_key: $("model-key").value,
  };
}
async function saveModel() {
  await api("settings", modelValues());
  $("model-key").value = "";
  if (state?.config.model_key_set)
    $("model-key").placeholder = "已保存 · 留空保留";
}
$("model-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "model-result", async () => {
    await saveModel();
    return "已保存。选择真实 AI 后可回鱼缸聊天。";
  });
});
$("test-model").addEventListener("click", (e) =>
  action(e.currentTarget, "model-result", async () => {
    await saveModel();
    const d = await api("model/test", {});
    return d.detail + "\n" + d.reply;
  }),
);
$("provider").addEventListener("change", () => {
  if ($("provider").value === "deepseek") {
    $("base-url").value = "https://api.deepseek.com";
    $("model").value = "deepseek-flash";
  }
  if ($("provider").value === "local") {
    $("base-url").value = "http://127.0.0.1:11434/v1";
    $("model").value = "";
    $("model").placeholder = "填写本机已安装的模型名";
    $("model-key").placeholder = "本地接口可填 local";
  }
});
$("persona-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "persona-result", async () => {
    await api("settings", {
      personality: $("personality").value,
      browser_steps: Number($("browser-steps").value),
    });
  });
});
async function saveQQ() {
  await api("settings", {
    onebot_url: $("onebot-url").value,
    onebot_token: $("onebot-token").value,
    qq_users: $("qq-users").value,
    qq_groups: $("qq-groups").value,
    qq_auto: $("qq-auto").checked,
  });
  $("onebot-token").value = "";
}
$("qq-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "qq-result", async () => {
    await saveQQ();
    return $("qq-auto").checked
      ? "已开启允许范围内的自动回复。请确认消息上报已配置。"
      : "QQ 设置已保存，自动回复关闭。";
  });
});
$("test-qq").addEventListener("click", (e) =>
  action(e.currentTarget, "qq-result", async () => {
    await saveQQ();
    return (await api("qq/test", {})).detail;
  }),
);
$("qq-setup").addEventListener("click", async () => {
  try {
    const d = await api("qq/setup", {});
    $("qq-setup-text").textContent =
      "上报地址：" + d.url + "\nSecret：" + d.secret;
    $("qq-setup-text").hidden = false;
  } catch (e) {
    toast(e.message);
  }
});
$("wechat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "wechat-result", async () => {
    await api("settings", { wecom_webhook: $("wecom-webhook").value });
    $("wecom-webhook").value = "";
    return "已保存。用下面的发送框发送成功后，连接才会标记为已验证。";
  });
});
$("send-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "send-result", async () => {
    const channel = $("send-channel").value;
    await api("send", {
      channel: channel === "qq-group" ? "qq" : channel,
      group: channel === "qq-group",
      target: $("send-target").value,
      message: $("outgoing").value,
    });
    return "渠道已确认发送成功";
  });
});
$("task-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "task-result", async () => {
    await api("tasks", {
      kind: $("task-kind").value,
      url: $("url").value,
      goal: $("goal").value,
      seconds: Number($("seconds").value),
    });
    return "任务已排队，请查看右侧执行记录。";
  });
});
$("scan-devices").addEventListener("click", (e) =>
  action(e.currentTarget, "phone-result", async () => {
    const d = await api("devices");
    $("device").replaceChildren();
    d.devices.forEach((x) => {
      const o = el("option", "", x.serial + " · " + x.status);
      o.value = x.serial;
      o.disabled = x.status !== "device";
      $("device").append(o);
    });
    const count = d.devices.filter((x) => x.status === "device").length;
    $("device-note").textContent = count
      ? "已检测到 " + count + " 台授权设备。"
      : "未检测到已授权设备，请检查 ADB、USB 连接及手机上的授权弹窗。";
    return count ? "请选择设备后开始。" : "没有可用设备。";
  }),
);
$("phone-form").addEventListener("submit", (e) => {
  e.preventDefault();
  action(e.submitter, "phone-result", async () => {
    if (!$("device").value) throw Error("请先检测并选择一台已授权设备");
    await api("tasks", {
      kind: "phone",
      serial: $("device").value,
      package: $("package").value,
      seconds: Number($("phone-seconds").value),
    });
    return "手机任务已提交，在探索日记中查看执行情况。";
  });
});
$("pause").addEventListener("click", async () => {
  try {
    await api("pause", {});
    $("qq-auto").checked = false;
    toast(
      "已关闭 QQ 自动回复，并停止后续浏览与手机动作。正在进行的网络请求可能需数秒结束。",
    );
    await refresh();
  } catch (e) {
    toast(e.message);
  }
});
$("clear-chat").addEventListener("click", async () => {
  if (!confirm("清空本机网页聊天记录？QQ 会话不会被删除。")) return;
  try {
    await api("chat/clear", {});
    await refresh();
  } catch (e) {
    toast(e.message);
  }
});
$("export").addEventListener("click", async () => {
  try {
    const d = await api("export");
    const blob = new Blob([JSON.stringify(d, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob),
      a = el("a");
    a.href = url;
    a.download = "大肥鱼记忆.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    toast(e.message);
  }
});
document
  .querySelectorAll(".refresh")
  .forEach((b) =>
    b.addEventListener("click", () => refresh().catch((e) => toast(e.message))),
  );
(async () => {
  try {
    const d = await api("bootstrap");
    token = d.token;
    const hash = location.hash.slice(1);
    if (labels[hash]) tab(hash);
    await refresh();
    if (hash === "connect") openDeepSeek();
    setInterval(() => refresh().catch(() => {}), 4000);
  } catch (e) {
    toast("无法连接本机服务：" + e.message);
  }
})();

function savePetPrefs() {
  petVersion++;
  petPrefsPending++;
  const update = { pet_form: pet.form, pet_motion: pet.motion };
  petSave = petSave
    .catch(() => {})
    .then(() => api("settings", update))
    .catch((e) => toast(e.message))
    .finally(() => {
      petPrefsPending--;
    });
}
for (const form of ["chibi", "mature"])
  $("form-" + form).addEventListener("click", () => {
    pet.setForm(form);
    savePetPrefs();
    $("pet-speech").textContent =
      form === "mature"
        ? "换个成熟的样子，继续陪你。"
        : "变成小小一只，也要大口吃饭。";
  });
$("pet-wave").addEventListener("click", () => pet.play("wave"));
$("pet-jump").addEventListener("click", () => pet.play("jump"));
$("pet-sleep").addEventListener("click", () =>
  pet.play(pet.action === "sleep" ? "idle" : "sleep"),
);
$("pet-motion").addEventListener("click", () => {
  pet.setMotion(!pet.motion);
  savePetPrefs();
});
$("pet-canvas").addEventListener("petstate", (e) => {
  const d = e.detail;
  for (const form of ["chibi", "mature"]) {
    $("form-" + form).classList.toggle("selected", d.form === form);
    $("form-" + form).setAttribute("aria-pressed", String(d.form === form));
  }
  $("pet-status").textContent =
    (d.form === "chibi" ? "Q 版" : "成熟版") +
    " · " +
    (pet.spec?.actions[d.action] || "待机");
  $("pet-motion").textContent = d.motion ? "暂停动画" : "开启动画";
  $("pet-motion").setAttribute("aria-pressed", String(d.motion));
  $("pet-sleep").textContent = d.action === "sleep" ? "叫醒她" : "睡一会儿";
});
$("launch-desktop").addEventListener("click", (e) =>
  action(e.currentTarget, "desktop-result", async () => {
    const d = await api("desktop/start", {});
    return d.detail;
  }),
);

function openDeepSeek() {
  const dialog = $("deepseek-dialog");
  if (dialog.open) return;
  const official =
    state?.config.base_url &&
    new URL(state.config.base_url).hostname === "api.deepseek.com";
  $("deepseek-key").placeholder =
    official && state.config.model_key_set
      ? "已保存 DeepSeek Key，留空继续使用"
      : "粘贴 API Key，而非登录密码";
  $("deepseek-account").hidden = true;
  $("deepseek-success").hidden = true;
  $("deepseek-model").replaceChildren(el("option", "", "自动选择当前可用模型"));
  $("deepseek-model").firstChild.value = "";
  result("deepseek-result", "");
  dialog.showModal();
}
document
  .querySelectorAll("[data-connect]")
  .forEach((b) => b.addEventListener("click", openDeepSeek));
$("deepseek-close").addEventListener("click", () =>
  $("deepseek-dialog").close(),
);
$("deepseek-dialog").addEventListener("cancel", (e) => {
  if (deepseekBusy) e.preventDefault();
});
$("deepseek-dialog").addEventListener("close", () => {
  $("deepseek-key").value = "";
  $("deepseek-key").type = "password";
  $("deepseek-reveal").textContent = "显示";
});
$("deepseek-reveal").addEventListener("click", () => {
  const show = $("deepseek-key").type === "password";
  $("deepseek-key").type = show ? "text" : "password";
  $("deepseek-reveal").textContent = show ? "隐藏" : "显示";
});
$("deepseek-key").addEventListener("input", () => {
  $("deepseek-key").type = "password";
  $("deepseek-reveal").textContent = "显示";
  $("deepseek-success").hidden = true;
  $("deepseek-account").hidden = true;
});
function showDeepSeekAccount(d) {
  const selection = $("deepseek-model").value;
  $("deepseek-model").replaceChildren();
  for (const m of d.models) {
    const o = el("option", "", m.name);
    o.value = m.id;
    $("deepseek-model").append(o);
  }
  $("deepseek-model").value = d.models.some((m) => m.id === selection)
    ? selection
    : d.recommended;
  $("deepseek-account").hidden = false;
  $("deepseek-account").classList.toggle("warning", !d.can_chat);
  $("deepseek-account").textContent =
    d.detail +
    "\n" +
    d.balances.map((b) => b.currency + " " + b.total_balance).join(" · ");
}
async function deepSeekAction(connect) {
  if (deepseekBusy) return;
  deepseekBusy = true;
  for (const id of ["deepseek-inspect", "deepseek-connect", "deepseek-close"])
    $(id).disabled = true;
  result(
    "deepseek-result",
    connect
      ? "正在检测模型、余额并发送一次简短请求……"
      : "正在检测 Key、模型与余额……",
  );
  try {
    const d = await api("deepseek/" + (connect ? "connect" : "inspect"), {
      api_key: $("deepseek-key").value.trim(),
      model: $("deepseek-model").value,
    });
    showDeepSeekAccount(d);
    result("deepseek-result", d.detail, !d.can_chat);
    if (connect) {
      $("deepseek-key").value = "";
      $("deepseek-success").hidden = false;
      $("deepseek-reply").textContent = d.reply;
      populated = false;
      await refresh();
    }
  } catch (e) {
    result("deepseek-result", e.message, true);
  } finally {
    deepseekBusy = false;
    for (const id of ["deepseek-inspect", "deepseek-connect", "deepseek-close"])
      $(id).disabled = false;
  }
}
$("deepseek-inspect").addEventListener("click", () => deepSeekAction(false));
$("deepseek-form").addEventListener("submit", (e) => {
  e.preventDefault();
  deepSeekAction(true);
});
$("deepseek-return").addEventListener("click", () => {
  $("deepseek-dialog").close();
  tab("home");
  $("message").focus();
});
$("forget-model").addEventListener("click", async (e) => {
  if (!confirm("忘记本机保存的模型密钥，并关闭 QQ 自动回复？聊天记录会保留。"))
    return;
  await action(e.currentTarget, "model-result", async () => {
    const d = await api("deepseek/disconnect", {});
    populated = false;
    return d.detail;
  });
});

$("diagnostics").addEventListener("click", async () => {
  try {
    const d = await api("diagnostics", {});
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }),
    );
    const a = el("a");
    a.href = url;
    a.download = "大肥鱼环境诊断.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    toast(e.message);
  }
});
window.addEventListener("hashchange", () => {
  const hash = location.hash.slice(1);
  if (hash === "connect" && token && state) openDeepSeek();
  else if (labels[hash]) tab(hash);
});
