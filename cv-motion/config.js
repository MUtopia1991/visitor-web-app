// ============================================================================
//  CV MOTION STUDIO — SETTINGS
//  Everything the video shows is driven from this file. Change a value,
//  reload studio.html (or re-run render.mjs) and the video updates.
//  No AI-generated images anywhere: every platform, prop, logo board and the
//  voxel character are built from these settings in code.
// ============================================================================

window.CV_CONFIG = {
  video: {
    width: 1920,
    height: 1080,
    fps: 30,
    duration: 60,          // seconds — total length of the piece
  },

  theme: {
    bgTop: "#0a0f2c",
    bgBottom: "#151b45",
    glow: "#2a3a8f",
    text: "#ffffff",
    muted: "#aeb7dc",
    accent: "#ffb648",     // global accent (timeline, badges, name underline)
    card: "rgba(9, 13, 38, 0.74)",
    cardBorder: "rgba(255,255,255,0.10)",
    path: "#2a3566",       // connecting walkway between career stops
    platformBase: "#1b2250",
    display: '"Space Grotesk", "Inter", sans-serif',
    body: '"Inter", "Space Grotesk", sans-serif',
  },

  person: {
    name: "Mohammad Nasravi",
    headline: "AI Creative Director · Export Marketing · Author",
    location: "Tehran, Iran",
    tagline: "A career, built block by block.",
    badge: "BUILT 100% IN CODE",
    corner: "MOHAMMAD NASRAVI — ANIMATED CV",
  },

  // The voxel twin. Toggle the look here.
  character: {
    skin: "#f0c6a0",
    hair: "#24170f",
    beard: true,
    beardColor: "#2b1c12",
    glasses: false,
    glassesColor: "#1b1b1b",
    shirt: "#2f6df6",
    collar: "#ffffff",
    pants: "#1d2547",
    shoes: "#0d0d14",
  },

  timing: {
    intro: 6.0,            // seconds for the opening title
    outro: 7.0,            // seconds for the closing card
    transition: 1.0,       // camera move between stops (overlaps the end of a stop)
  },

  // Each career stop becomes an isometric platform that builds itself.
  // prop: antenna | books | desk | tower | globe | chocolate | toolkit
  stops: [
    {
      years: "2008 – 2011",
      title: "Computer Operator",
      org: "IRIB · National Broadcasting",
      board: "IRIB",
      color: "#e4556a",
      prop: "antenna",
      bullets: [
        "Kept live broadcast operations running",
        "First taste of media technology at scale",
      ],
    },
    {
      years: "2008 – 2014",
      title: "BA Persian Literature → MA Linguistics",
      org: "Allameh Tabataba'i University, Tehran",
      board: "ATU",
      color: "#47b5ff",
      prop: "books",
      bullets: [
        "Thesis on discourse reconstruction, graded 20/20",
        "Master's GPA 18.6 / 20",
      ],
    },
    {
      years: "2012 – 2016",
      title: "Researcher",
      org: "Institute of Imami Studies",
      board: "RESEARCH",
      color: "#8e6cf1",
      prop: "desk",
      bullets: [
        "Discourse analysis & utopian studies",
        "Peer-reviewed papers, talks in Lisbon, Gdańsk & Leuven",
      ],
    },
    {
      years: "2017 – 2018",
      title: "MA by Research (MRes)",
      org: "Royal Holloway, University of London",
      board: "RHUL",
      color: "#ff8a4c",
      prop: "tower",
      bullets: [
        "Thesis: Utopia in the Mirror of Pilgrimage",
        "Scholarship for academic excellence",
        "Arbaeen World Prize — best book, 2017",
      ],
    },
    {
      years: "2019 – 2023",
      title: "International Relations & Culture",
      org: "Ahlul Bayt Univ. · Public Culture Council · Council of Iranians Abroad",
      board: "GLOBAL",
      color: "#35d0a0",
      prop: "globe",
      bullets: [
        "Rolled out UNESCO's AI-ethics framework across departments",
        "Built AI-powered content to lift HR productivity",
        "Taught Persian to international students",
      ],
    },
    {
      years: "2025 – Present",
      title: "Export Specialist → AI Creative Director",
      org: "Shirin Asal Food Industrial Group",
      board: "SHIRIN ASAL",
      color: "#ffc233",
      prop: "chocolate",
      bullets: [
        "Cinematic AI commercials for Gulf, UK, US, AU & CA markets",
        "Campaigns for Gulfood 2026, Canton Fair 2025, ISM Middle East",
        "Shipped a lead-capture app for the trade-show booth",
      ],
    },
    {
      years: "Toolkit",
      title: "Author · Linguist · Builder",
      org: "3 books · Utopian Studies journal (2025) · Persian, Arabic, English",
      board: "TOOLKIT",
      color: "#ff5fa2",
      prop: "toolkit",
      bullets: [
        "Generative video, voice & image pipelines",
        "Brand storytelling rooted in cultural anthropology",
        "Code-first motion design — like this video",
      ],
    },
  ],

  outro: {
    line: "Let's build something worth watching.",
    links: ["nasravi.com", "linkedin.com/in/mohammad-nasravi", "mnasravia@gmail.com"],
  },
};
