"use strict";
const messages = {
  "en": {
    "subtitle": "Connected documentation",
    "readonly": "Read only",
    "language": "Language",
    "reload": "↻ Reload database",
    "find": "FIND INFORMATION",
    "searchPlaceholder": "Topic, title or ID…",
    "nodeType": "Node type",
    "allTypes": "All types",
    "nodes": "Database nodes",
    "results": "Search results",
    "start": "Start with the overview. Relationship explanations suggest your next step.",
    "graph": "Relationship graph",
    "scope": "Graph scope",
    "neighborhood": "Node neighborhood",
    "wholeGraph": "Whole graph",
    "depth": "Depth",
    "relationType": "Relationship type",
    "allRelations": "All relationships",
    "fit": "Fit",
    "fitTitle": "Fit graph",
    "interactiveGraph": "Interactive documentation graph",
    "emptyGraph": "No nodes match the selected filters.",
    "graphHelp": "Select a node · Wheel to zoom · Drag to pan",
    "zoomOut": "Zoom out",
    "zoomIn": "Zoom in",
    "content": "Node content",
    "back": "Back",
    "forward": "Forward",
    "copy": "Copy ID",
    "copied": "ID copied",
    "eyebrow": "DOCUMENTATION AS A GRAPH",
    "welcome": "From a question to useful knowledge",
    "welcomeText": "Choose a node in the list or graph to read its document and follow its connections.",
    "requestError": "Request failed",
    "unavailable": "Database unavailable",
    "repair": "Database unavailable. Fix errors and reload the database.",
    "invalid": "Database validation failed.",
    "valid": "Validation: no errors",
    "warnings": "Warnings: {count}",
    "missingNode": "Node “{id}” is missing. Opened an entry point.",
    "entry": "ENTRY",
    "noResults": "Nothing found.",
    "firstResults": "First 200 of {count}",
    "next": "Where to go next",
    "outgoing": "Outgoing relationships →",
    "incoming": "Incoming relationships ←",
    "noLinks": "No relationships.",
    "inView": "{counts} in view",
    "copyError": "Could not copy. ID: {id}",
    "nodeForms": [
      "node",
      "nodes",
      "nodes"
    ],
    "edgeForms": [
      "relationship",
      "relationships",
      "relationships"
    ],
    "types": {
      "system": "System",
      "concept": "Concept",
      "workflow": "Workflow",
      "tool": "Tool",
      "reference": "Reference"
    },
    "relations": {
      "contains": "Contains",
      "explains": "Explains",
      "requires": "Requires",
      "related": "Related"
    },
    "errors": {
      "INVALID_DATABASE": "Database validation failed.",
      "UNKNOWN_NODE": "Unknown node.",
      "INVALID_LANGUAGE": "Unsupported language.",
      "INVALID_ARGUMENT": "Invalid request parameter.",
      "INVALID_HOST": "Use the printed loopback address.",
      "IO_ERROR": "Could not read the database.",
      "NOT_FOUND": "Unknown route.",
      "READ_ONLY": "The viewer supports reading only.",
      "INVALID_MANIFEST": "Check graph.json structure and encoding.",
      "UNSUPPORTED_VERSION": "Only format version 1 is supported.",
      "INVALID_NODE": "Check required node fields.",
      "INVALID_ID": "Invalid node identifier.",
      "DUPLICATE_ID": "Duplicate node identifier.",
      "INVALID_NODE_TYPE": "Unsupported node type.",
      "INVALID_TAGS": "Tags must be a list of nonempty strings.",
      "INVALID_TRANSLATION": "Check translation fields.",
      "UNSAFE_CONTENT_PATH": "Document paths must stay inside the database.",
      "INVALID_DOCUMENT": "Check document existence and UTF-8 encoding.",
      "EMPTY_DOCUMENT": "A document is empty.",
      "EMPTY_GRAPH": "At least one node is required.",
      "MISSING_ENTRY_POINT": "At least one entry point is required.",
      "INVALID_ENTRY_POINT": "Entry points must refer to existing nodes.",
      "DUPLICATE_ENTRY_POINT": "Duplicate entry point.",
      "INVALID_EDGE": "Check required relationship fields.",
      "DANGLING_EDGE": "A relationship refers to a missing node.",
      "INVALID_RELATION": "Unsupported relationship type.",
      "DUPLICATE_EDGE": "Duplicate relationship.",
      "UNREACHABLE_NODE": "A node is disconnected from entry points."
    },
    "diagnosticHint": "Run knowledge-graph validate for full diagnostic details."
  },
  "ru": {
    "subtitle": "Граф документации",
    "readonly": "Только чтение",
    "language": "Язык",
    "reload": "↻ Обновить базу",
    "find": "НАЙТИ ИНФОРМАЦИЮ",
    "searchPlaceholder": "Тема, название или ID…",
    "nodeType": "Тип узла",
    "allTypes": "Все типы",
    "nodes": "Узлы базы",
    "results": "Результаты поиска",
    "start": "Начните с обзора. Пояснения связей подскажут следующий шаг.",
    "graph": "Граф связей",
    "scope": "Область графа",
    "neighborhood": "Окружение узла",
    "wholeGraph": "Весь граф",
    "depth": "Глубина",
    "relationType": "Тип связи",
    "allRelations": "Все связи",
    "fit": "Вместить",
    "fitTitle": "Вместить граф",
    "interactiveGraph": "Интерактивный граф документации",
    "emptyGraph": "Узлы не соответствуют выбранным фильтрам.",
    "graphHelp": "Выберите узел · Колесо — масштаб · Перетаскивание — перемещение",
    "zoomOut": "Уменьшить",
    "zoomIn": "Увеличить",
    "content": "Содержимое узла",
    "back": "Назад",
    "forward": "Вперёд",
    "copy": "Копировать ID",
    "copied": "ID скопирован",
    "eyebrow": "ДОКУМЕНТАЦИЯ КАК ГРАФ",
    "welcome": "От вопроса — к нужному знанию",
    "welcomeText": "Выберите узел в списке или на графе, чтобы прочитать документ и перейти по его связям.",
    "requestError": "Ошибка запроса",
    "unavailable": "База недоступна",
    "repair": "База недоступна. Исправьте ошибки и нажмите «Обновить базу».",
    "invalid": "База не прошла проверку.",
    "valid": "Проверка: без ошибок",
    "warnings": "Предупреждений: {count}",
    "missingNode": "Узел «{id}» отсутствует. Открыта точка входа.",
    "entry": "ВХОД",
    "noResults": "Ничего не найдено.",
    "firstResults": "Первые 200 из {count}",
    "next": "Куда перейти дальше",
    "outgoing": "Исходящие связи →",
    "incoming": "Входящие связи ←",
    "noLinks": "Связей нет.",
    "inView": "{counts} в представлении",
    "copyError": "Не удалось скопировать. ID: {id}",
    "nodeForms": [
      "узел",
      "узла",
      "узлов"
    ],
    "edgeForms": [
      "связь",
      "связи",
      "связей"
    ],
    "types": {
      "system": "Система",
      "concept": "Понятие",
      "workflow": "Процесс",
      "tool": "Инструмент",
      "reference": "Справочник"
    },
    "relations": {
      "contains": "Содержит",
      "explains": "Объясняет",
      "requires": "Требует",
      "related": "Связано"
    },
    "errors": {
      "INVALID_DATABASE": "База не прошла проверку.",
      "UNKNOWN_NODE": "Узел не найден.",
      "INVALID_LANGUAGE": "Язык не поддерживается.",
      "INVALID_ARGUMENT": "Некорректный параметр запроса.",
      "INVALID_HOST": "Используйте указанный локальный адрес.",
      "IO_ERROR": "Не удалось прочитать базу.",
      "NOT_FOUND": "Адрес не найден.",
      "READ_ONLY": "Просмотрщик доступен только для чтения.",
      "INVALID_MANIFEST": "Проверьте структуру и кодировку graph.json.",
      "UNSUPPORTED_VERSION": "Поддерживается только версия формата 1.",
      "INVALID_NODE": "Проверьте обязательные поля узла.",
      "INVALID_ID": "Некорректный ID узла.",
      "DUPLICATE_ID": "Повторяющийся ID узла.",
      "INVALID_NODE_TYPE": "Недопустимый тип узла.",
      "INVALID_TAGS": "Теги должны быть списком непустых строк.",
      "INVALID_TRANSLATION": "Проверьте поля перевода.",
      "UNSAFE_CONTENT_PATH": "Пути документов должны оставаться внутри базы.",
      "INVALID_DOCUMENT": "Проверьте существование и UTF-8 кодировку документа.",
      "EMPTY_DOCUMENT": "Документ пуст.",
      "EMPTY_GRAPH": "Требуется хотя бы один узел.",
      "MISSING_ENTRY_POINT": "Требуется хотя бы одна точка входа.",
      "INVALID_ENTRY_POINT": "Точки входа должны ссылаться на существующие узлы.",
      "DUPLICATE_ENTRY_POINT": "Повторяющаяся точка входа.",
      "INVALID_EDGE": "Проверьте обязательные поля связи.",
      "DANGLING_EDGE": "Связь ссылается на отсутствующий узел.",
      "INVALID_RELATION": "Недопустимый тип связи.",
      "DUPLICATE_EDGE": "Повторяющаяся связь.",
      "UNREACHABLE_NODE": "Узел не связан с точками входа."
    },
    "diagnosticHint": "Для подробной диагностики запустите knowledge-graph validate."
  }
};
let language = "en";
const explicitLanguage = new URLSearchParams(location.search).get("lang");
if (["en", "ru"].includes(explicitLanguage)) language = explicitLanguage;
else {
  try {
    const stored = localStorage.getItem("knowledge-graph-language");
    if (["en", "ru"].includes(stored)) language = stored;
  } catch { /* Optional browser storage. */ }
}
function t(key, values = {}) {
  return messages[language][key].replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}
function applyLanguage() {
  document.documentElement.lang = language;
  document.querySelectorAll("[data-i18n]").forEach(node => { node.textContent = t(node.dataset.i18n); });
  for (const [suffix, attribute] of [["aria", "aria-label"], ["title", "title"], ["placeholder", "placeholder"]]) {
    document.querySelectorAll(`[data-i18n-${suffix}]`).forEach(node => node.setAttribute(attribute, t(node.getAttribute(`data-i18n-${suffix}`))));
  }
  document.getElementById("language").value = language;
}
