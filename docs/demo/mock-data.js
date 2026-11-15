/* Mock Home Assistant states for PowerSchool card demo */
(function () {
  const now = new Date().toISOString();
  function S(id, state, attrs) {
    return {
      entity_id: id,
      state: String(state),
      last_updated: now,
      last_changed: now,
      attributes: Object.assign({ friendly_name: id }, attrs || {}),
    };
  }

  const trentCourses = [
    {
      id: "sensor.powerschool_trent_symphonic_band",
      name: "Symphonic Band",
      pct: 96,
      teacher: "Ms. Rivera",
      room: "B12",
      section_id: "52076",
      assignments: [
        { name: "Concert reflection", due: "2026-11-17", percent: null },
        { name: "Scale quiz", due: "2026-11-12", percent: 100 },
      ],
    },
    {
      id: "sensor.powerschool_trent_science_7",
      name: "Science 7",
      pct: 88,
      teacher: "Mr. Chen",
      room: "C4",
      section_id: "51672",
      assignments: [
        { name: "Lab write-up", due: "2026-11-16", percent: null },
        { name: "Chapter 4 quiz", due: "2026-11-10", percent: 85 },
      ],
      missing: 0,
      late: 0,
    },
    {
      id: "sensor.powerschool_trent_english_language_arts_7",
      name: "English Language Arts 7",
      pct: 91,
      teacher: "Mrs. Brooks",
      room: "A8",
      section_id: "49916",
      assignments: [
        { name: "Essay draft", due: "2026-11-18", percent: null },
        { name: "Vocab set 6", due: "2026-11-14", percent: 90 },
      ],
    },
    {
      id: "sensor.powerschool_trent_pre_algebra",
      name: "Pre-Algebra",
      pct: 84,
      teacher: "Mr. Ortiz",
      room: "D2",
      section_id: "51669",
      assignments: [
        { name: "Problem set 12", due: "2026-11-17", percent: null, late: false },
        { name: "Quiz 5", due: "2026-11-08", percent: 78 },
      ],
      missing: 1,
      late: 0,
    },
    {
      id: "sensor.powerschool_trent_global_studies_7",
      name: "Global Studies 7",
      pct: 93,
      teacher: "Ms. Patel",
      room: "A3",
      section_id: "49925",
      assignments: [
        { name: "Map activity", due: "2026-11-19", percent: null },
      ],
    },
  ];

  const teaganCourses = [
    {
      id: "sensor.powerschool_teagan_reading",
      name: "Reading",
      pct: null,
      teacher: "Ms. Hall",
      room: "101",
      section_id: "60001",
      assignments: [{ name: "Book log", due: "2026-11-18", percent: null }],
      grade_letter: null,
    },
    {
      id: "sensor.powerschool_teagan_math",
      name: "Math",
      pct: null,
      teacher: "Mr. Lee",
      room: "102",
      section_id: "60002",
      assignments: [],
    },
  ];

  function courseState(c, student) {
    const a = {
      student,
      course: c.name,
      teacher: c.teacher || "",
      room: c.room || "",
      section_id: c.section_id,
      assignments: c.assignments || [],
      missing: c.missing || 0,
      late: c.late || 0,
      absences: c.absences || 0,
      tardies: c.tardies || 0,
      unit_of_measurement: c.pct != null ? "%" : undefined,
    };
    if (c.pct != null) a.grade_percent = c.pct;
    if (c.grade_letter) a.grade_letter = c.grade_letter;
    const state = c.pct != null ? c.pct : "unknown";
    return S(c.id, state, a);
  }

  const states = {};

  [
    S("sensor.powerschool_trent_grade_average", 90.4, {
      student: "Trent",
      unit_of_measurement: "%",
    }),
    S("sensor.powerschool_trent_missing_assignments", 1, { student: "Trent" }),
    S("sensor.powerschool_trent_late_assignments", 0, { student: "Trent" }),
    S("sensor.powerschool_trent_due_soon_assignments", 4, {
      student: "Trent",
      window_days: 7,
      assignments: [
        { name: "Lab write-up", course: "Science 7", due: "2026-11-16", percent: null },
        { name: "Concert reflection", course: "Symphonic Band", due: "2026-11-17", percent: null },
        { name: "Problem set 12", course: "Pre-Algebra", due: "2026-11-17", percent: null },
        { name: "Essay draft", course: "English Language Arts 7", due: "2026-11-18", percent: null },
      ],
    }),
    S("sensor.powerschool_trent_absences", 2, { student: "Trent" }),
    S("sensor.powerschool_trent_tardies", 1, { student: "Trent" }),
    S("sensor.powerschool_trent_absent_days", 2, { student: "Trent" }),
    S("sensor.powerschool_trent_tardy_days", 1, { student: "Trent" }),
    S("sensor.powerschool_trent_class_roster", 5, {
      student: "Trent",
      class_roster: trentCourses.map((c) => ({
        course: c.name,
        teacher: c.teacher,
        room: c.room,
      })),
    }),
  ].forEach((e) => (states[e.entity_id] = e));

  trentCourses.forEach((c) => {
    const e = courseState(c, "Trent");
    states[e.entity_id] = e;
  });

  [
    S("sensor.powerschool_teagan_grade_average", "unknown", { student: "Teagan" }),
    S("sensor.powerschool_teagan_missing_assignments", 0, { student: "Teagan" }),
    S("sensor.powerschool_teagan_late_assignments", 0, { student: "Teagan" }),
    S("sensor.powerschool_teagan_due_soon_assignments", 1, {
      student: "Teagan",
      window_days: 7,
      assignments: [
        { name: "Book log", course: "Reading", due: "2026-11-18", percent: null },
      ],
    }),
    S("sensor.powerschool_teagan_absences", 0, { student: "Teagan" }),
    S("sensor.powerschool_teagan_tardies", 0, { student: "Teagan" }),
    S("sensor.powerschool_teagan_class_roster", 2, {
      student: "Teagan",
      class_roster: teaganCourses.map((c) => ({
        course: c.name,
        teacher: c.teacher,
        room: c.room,
      })),
    }),
  ].forEach((e) => (states[e.entity_id] = e));

  teaganCourses.forEach((c) => {
    const e = courseState(c, "Teagan");
    states[e.entity_id] = e;
  });

  window.PS_DEMO_HASS = {
    states,
    callService: async () => {},
    connection: { subscribeEvents: () => () => {} },
  };
})();
