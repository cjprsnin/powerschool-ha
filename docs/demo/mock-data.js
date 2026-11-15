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
        { name: "Problem set 12", due: "2026-11-17", percent: null },
        { name: "Quiz 5", due: "2026-11-08", percent: 78 },
      ],
      missing: 1,
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
    // V2 derives tile title from friendly_name (strips "PowerSchool {student} ").
    // V3/V4 prefer attributes.course. Set both.
    const a = {
      student,
      course: c.name,
      friendly_name: "PowerSchool " + student + " " + c.name,
      teacher: c.teacher || "",
      room: c.room || "",
      section_id: c.section_id,
      assignments: c.assignments || [],
      missing: c.missing || 0,
      late: c.late || 0,
      absences: c.absences || 0,
      tardies: c.tardies || 0,
    };
    if (c.pct != null) {
      a.grade_percent = c.pct;
      a.unit_of_measurement = "%";
    }
    if (c.grade_letter) a.grade_letter = c.grade_letter;
    return S(c.id, c.pct != null ? c.pct : "unknown", a);
  }

  const states = {};

  function addSummary(student, avg, missing, late, dueCount, dueList, abs, tardy, roster) {
    const slug = student.toLowerCase();
    const base = "sensor.powerschool_" + slug + "_";
    [
      S(base + "grade_average", avg, {
        student,
        friendly_name: "PowerSchool " + student + " Grade Average",
        unit_of_measurement: avg === "unknown" ? undefined : "%",
      }),
      S(base + "missing_assignments", missing, {
        student,
        friendly_name: "PowerSchool " + student + " Missing Assignments",
      }),
      S(base + "late_assignments", late, {
        student,
        friendly_name: "PowerSchool " + student + " Late Assignments",
      }),
      S(base + "due_soon_assignments", dueCount, {
        student,
        friendly_name: "PowerSchool " + student + " Due Soon Assignments",
        window_days: 7,
        assignments: dueList,
      }),
      S(base + "upcoming_assignments", dueCount, {
        student,
        friendly_name: "PowerSchool " + student + " Upcoming Assignments",
        window_days: 14,
        assignments: dueList,
      }),
      S(base + "absences", abs, {
        student,
        friendly_name: "PowerSchool " + student + " Absences",
      }),
      S(base + "tardies", tardy, {
        student,
        friendly_name: "PowerSchool " + student + " Tardies",
      }),
      S(base + "absent_days", abs, {
        student,
        friendly_name: "PowerSchool " + student + " Absent Days",
      }),
      S(base + "tardy_days", tardy, {
        student,
        friendly_name: "PowerSchool " + student + " Tardy Days",
      }),
      S(base + "class_roster", roster.length, {
        student,
        friendly_name: "PowerSchool " + student + " Class Roster",
        class_roster: roster.map((c) => ({
          course: c.name,
          teacher: c.teacher,
          room: c.room,
        })),
      }),
    ].forEach((e) => {
      states[e.entity_id] = e;
    });
  }

  addSummary(
    "Trent",
    90.4,
    1,
    0,
    4,
    [
      { name: "Lab write-up", course: "Science 7", due: "2026-11-16", percent: null },
      { name: "Concert reflection", course: "Symphonic Band", due: "2026-11-17", percent: null },
      { name: "Problem set 12", course: "Pre-Algebra", due: "2026-11-17", percent: null },
      { name: "Essay draft", course: "English Language Arts 7", due: "2026-11-18", percent: null },
    ],
    2,
    1,
    trentCourses
  );
  trentCourses.forEach((c) => {
    const e = courseState(c, "Trent");
    states[e.entity_id] = e;
  });

  addSummary(
    "Teagan",
    "unknown",
    0,
    0,
    1,
    [{ name: "Book log", course: "Reading", due: "2026-11-18", percent: null }],
    0,
    0,
    teaganCourses
  );
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
