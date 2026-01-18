from kivy.animation import Animation
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText  # v2 API
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

# Standardized imports with fallback for direct execution
try:
    from module.services import (
        compute_positions,
        list_open_view_rows,
        search_charts,
        build_chart_instance,
        find_chart_by_name_or_id,
        build_radix_figure_for_chart,
    )
    from module.utils import (
        Actual, combine_date_time, now_utc, 
        prepare_horoscope, default_ephemeris_path, 
        import_chart_yaml, read_yaml_file, write_yaml_file
    )
    from module.workspace import (
        change_language, load_workspace, init_workspace,
        add_or_update_chart, save_workspace_modular, summarize_chart,
        add_subject, scan_workspace_changes,
    )
    from module.z_visual import build_radix_figure, write_plotly_html
except ImportError:
    from services import (
        compute_positions,
        list_open_view_rows,
        search_charts,
        build_chart_instance,
        find_chart_by_name_or_id,
        build_radix_figure_for_chart,
    )
    from utils import (
        Actual, combine_date_time, now_utc, 
        prepare_horoscope, default_ephemeris_path, 
        import_chart_yaml, read_yaml_file, write_yaml_file
    )
    from workspace import (
        change_language, load_workspace, init_workspace,
        add_or_update_chart, save_workspace_modular, summarize_chart,
        add_subject, scan_workspace_changes,
    )
    from z_visual import build_radix_figure, write_plotly_html

try:
    from module.models import EngineType, ChartInstance, ChartSubject, ChartConfig, HouseSystem, ChartMode
except Exception:
    from models import EngineType, ChartInstance, ChartSubject, ChartConfig, HouseSystem, ChartMode
try:
    # Kivy Garden WebView for interactive Plotly in-app
    from kivy_garden.webview import WebView  # noqa: F401 (used in KV)
    WEBVIEW_OK = True
except Exception:
    WEBVIEW_OK = False

from pathlib import Path

class MyApp(MDApp):
    # top-level view: "aspects", "transits", "progressions", "synastry"
    current_view = StringProperty("general")
    current_view_title = StringProperty("General")
    # charts
    charts = ListProperty([])
    current_person_index = NumericProperty(0)
    current_person_name = StringProperty("")
    # engine settings (optional)
    engine_mode = StringProperty("default")  # values: "default" (swisseph) or "jpl"; prefer swisseph by default
    ephemeris_file = StringProperty("")
    workspace_dir = StringProperty("")
    # center content mode: overview | chart_settings | chart | general | chart_create | open_view
    center_mode = StringProperty("general")
    # state for chart create
    chart_type = StringProperty("NATAL")

    def build(self):
        self.title = "Kefer Astrology"
        # KivyMD v2 theming examples (optional)
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"  # unify on light mode for now
        return Builder.load_file("ui_kivy.kv")

    def on_start(self):
        # move initialization here so UI is ready
        self.prepare_content()
        # ensure UI reflects defaults
        self._update_person_buttons()
        self._update_view_title()
        # default ephemeris path (if JPL used)
        self.ephemeris_file = default_ephemeris_path()
        # Prepare WebView container if available
        if WEBVIEW_OK:
            self._ensure_webview()
        # Capture default left-pane widgets defined in KV so we can restore them later
        try:
            left = self.root.ids.get('left_col')
            if left is not None:
                # children order in Kivy is reverse of addition; store a copy
                self._left_defaults = left.children[:]
        except Exception:
            self._left_defaults = []
        # First-run: try open hardcoded dir; else wizard
        default_path = Path("/home/jav/Documents/Space/aaaaaaaaaaaaa/")
        if default_path.is_dir() and (default_path / "workspace.yaml").exists():
            try:
                self.workspace_dir = str(default_path)
                self.workspace = load_workspace(str(default_path / "workspace.yaml"))
                # populate charts
                self.charts = [getattr(getattr(c, 'subject', None), 'name', '') for c in (self.workspace.charts or []) if getattr(getattr(c, 'subject', None), 'name', '')]
                if self.charts:
                    self.current_person_name = self.charts[0]
                self._update_person_buttons()
                # Focus first chart so actions like Export work immediately
                try:
                    if self.charts:
                        self._focus_chart_by_name(self.charts[0])
                except Exception:
                    pass
                # initial view: chart icon (create)
                self.on_toolbar("chart_settings")
            except Exception as e:
                self.show_message(f"Failed to open default workspace: {e}")
                self._prompt_workspace_selection()
        else:
            self._prompt_workspace_selection()

    # ---------- domain init ----------
    def prepare_content(self, date: str="", place: str=""):
        # 1 - initial setting
        # Initialize your domain objects here (avoid touching widgets until on_start)
        # Do not geocode on startup to avoid hitting Nominatim unnecessarily
        self.location = None
        #self.name = ""
        self.chart = None
        self.workspace = None
    
    # ---------- toolbar actions (non-top-level ones) ----------
    def on_toolbar(self, action: str):
        action = (action or "").strip().lower()
        if action == "new_chart":
            # Switch to chart creation center view
            self.center_mode = "chart_create"
            self._render_chart_create_view()
            return
        if action == "open_chart":
            # show open view (database + my horoscopes)
            self.center_mode = "open_view"
            self._render_open_chart_view()
            return
        if action == "open_workspace":
            self._popup_open_workspace()
            return
        if action == "save_chart":
            # explicit save if user wants it; usually auto-saved already
            self._save_workspace()
            return
        if action == "export_chart":
            self._popup_export_chart()
            return
        if action == "settings":
            self.center_mode = "settings"
            self._render_settings_view()
            return
        if action == "chart_settings":
            self.center_mode = "chart_settings"
            self._render_chart_settings()
            return
        # defaults: just toast
        self.show_message(f"{action.replace('_', ' ').title()} clicked")

    # ---------- top-level view switching ----------
    def set_view(self, name: str):
        name = (name or "").lower()
        titles = {
            "general": "General",
        }
        if name not in titles:
            return
        self.current_view = name
        self.current_view_title = titles[name]

    def _update_view_title(self):
        titles = {
            "general": "General",
        }
        self.current_view_title = titles.get(self.current_view, "General")

    # ---------- person switching ----------
    def set_person(self, index: int):
        if not (0 <= index < len(self.charts)):
            return
        self.current_person_index = index
        self.current_person_name = self.charts[index]
        # reflect in inputs
        ids = self.root.ids
        if "subject_name" in ids:
            ids["subject_name"].text = self.current_person_name
        # update chip-like buttons
        self._update_person_buttons()
        # focus matching chart and update header
        try:
            self._focus_chart_by_name(self.current_person_name)
        except Exception:
            try:
                ids.get('view_label').text = f"[b]{self.current_view_title}[/b] — {self.current_person_name}"
            except Exception:
                pass
        # refresh settings view if active
        if self.center_mode == "chart_settings":
            try:
                self._render_chart_settings()
            except Exception:
                pass

    def _update_person_buttons(self):
        ids = self.root.ids
        row = ids.get('people_row')
        if row is None:
            return
        # rebuild dynamic chip buttons
        try:
            row.clear_widgets()
        except Exception:
            pass
        from kivymd.uix.button import MDButton, MDButtonText
        for i, name in enumerate(self.charts or []):
            try:
                btn = MDButton(style=('filled' if i == self.current_person_index else 'text'), size_hint_y=None, height=36)
                btn.add_widget(MDButtonText(text=name or '-'))
                btn.bind(on_release=lambda _b, idx=i: self.set_person(idx))
                row.add_widget(btn)
            except Exception:
                continue

    # ---------- expand/collapse sections ----------
    def toggle_section(self, which: str):
        ids = self.root.ids
        mapping = {
            "subject": ids.get("subject_content"),
            "time": ids.get("time_content"),
            "transits": ids.get("transits_content"),
            "objects": ids.get("objects_content"),
        }
        content = mapping.get(which)
        if not content:
            return
        is_collapsed = content.height <= 1
        if is_collapsed:
            target = 200
            Animation.stop_all(content)
            Animation(height=target, opacity=1, d=0.18, t="out_quad").start(content)
        else:
            Animation.stop_all(content)
            Animation(height=0, opacity=0, d=0.18, t="out_quad").start(content)

    # ---------- Bottom pseudo-tabs ----------
    def set_tab(self, name: str):
        self.root.ids.tabs_manager.current = name

    def draw_content(self, name="Johny"):
        self.name = name

    # ---------- engine helper ----------
    def _effective_engine(self):
        try:
            ws = getattr(self, 'workspace', None)
            d = getattr(ws, 'default', None) if ws is not None else None
            eng = getattr(d, 'ephemeris_engine', None) if d is not None else None
            if eng:
                return eng
        except Exception:
            pass
        return EngineType.JPL

    def build_chart(self, name: str, dt, loc_text: str, mode: ChartMode = ChartMode.NATAL, tags: list | None = None):
        """Build a ChartInstance using services.build_chart_instance and store it in self.chart."""
        engine = self._effective_engine()
        eph = self.ephemeris_file if engine == EngineType.JPL else None
        chart = build_chart_instance(name=name, dt_str=str(dt), loc_text=loc_text, mode=mode, ws=getattr(self, 'workspace', None), ephemeris_path=eph)
        try:
            if tags:
                chart.tags = [t.strip() for t in tags if t and t.strip()]
        except Exception:
            pass
        self.chart = chart
        return self.chart

    def render_radix(self):
        """Render the standardized radix chart to interactive HTML and load it in the embedded WebView."""
        ids = self.root.ids
        name = ids.get("subject_name").text if ids.get("subject_name") else self.current_person_name
        name = (name or self.current_person_name or "Radix").strip() or "Radix"
        loc_text = ids.get("subject_place").text if ids.get("subject_place") else "Prague"
        loc_text = (loc_text or "Prague").strip() or "Prague"
        # Build datetime string from fields if available, else use now
        dt_str = None
        if ids.get("date_input") and ids.get("time_input"):
            ds = (ids["date_input"].text or "").strip()
            ts = (ids["time_input"].text or "").strip()
            if ds and ts:
                dt_str = f"{ds} {ts}"
        if not dt_str:
            dt_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        # Ensure chart exists (stores engine + eph settings)
        self.build_chart(name, dt_str, loc_text)
        engine = self._effective_engine()
        eph = self.ephemeris_file if engine == EngineType.JPL else None

        # Compute and build figure via services
        try:
            if getattr(self, 'chart', None) is not None:
                fig = build_radix_figure_for_chart(self.chart)
            else:
                positions = compute_positions(engine, name, dt_str, loc_text, ephemeris_path=eph)
                fig = build_radix_figure(positions)
        except Exception as e:
            self.show_message(f"Failed to compute figure: {e}")
            return

        # Embed interactive chart via WebView (create it dynamically)
        wv = self._ensure_webview()
        if not WEBVIEW_OK or wv is None:
            # Fallback: open in external browser
            try:
                import webbrowser
                out_path = write_plotly_html(fig, tmpname="radix_chart.html")
                webbrowser.open(f"file://{out_path}")
                self.show_message("Opened interactive chart in your default browser (install 'kivy_garden.webview' to embed).")
            except Exception as e:
                self.show_message(f"Failed to open browser: {e}")
            return
        try:
            out_path = write_plotly_html(fig, tmpname="radix_chart.html")
            # load into webview
            wv.url = f"file://{out_path}"
        except Exception as e:
            self.show_message(f"Failed to render interactive chart: {e}")

    # ---------- workspace selection & loading ----------
    def _prompt_workspace_selection(self):
        # Popup content
        box = BoxLayout(orientation='vertical', spacing=8, padding=8)
        box.add_widget(Label(text="Select a workspace folder", size_hint_y=None, height=30))
        # Start in current workspace dir if available; allow selecting directories
        try:
            start_path = self.workspace_dir if getattr(self, 'workspace_dir', None) else str(Path.cwd())
        except Exception:
            start_path = str(Path.cwd())
        chooser = FileChooserIconView(path=start_path, dirselect=True)
        box.add_widget(chooser)
        btns = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_cancel = self._md_button("Cancel", style="text", height=40)
        btn_select = self._md_button("Select", style="filled", height=40)
        btns.add_widget(btn_cancel)
        btns.add_widget(btn_select)
        box.add_widget(btns)
        popup = Popup(title="Workspace", content=box, size_hint=(0.9, 0.9), auto_dismiss=False)

        def on_cancel(*_):
            # Do not mutate current workspace or people on cancel
            popup.dismiss()

        def on_select(*_):
            sel = chooser.selection[0] if chooser.selection else chooser.path
            base = sel if Path(sel).is_dir() else str(Path(sel).parent)
            if not base:
                return
            # Initialize if no manifest exists (but do not touch current workspace on failure)
            manifest = str(Path(base) / "workspace.yaml")
            if not Path(manifest).exists():
                try:
                    init_workspace(
                        base_dir=base,
                        owner="User",
                        active_model="default",
                        default_ephemeris={"name": None, "backend": "swisseph"},
                    )
                except Exception as e:
                    self.show_message(f"Failed to init workspace: {e}")
                    return
                manifest = str(Path(base) / "workspace.yaml")
            # Try load into temp vars, then commit to app state on success
            try:
                ws = load_workspace(manifest)
                names = [getattr(getattr(c, 'subject', None), 'name', '') for c in (ws.charts or []) if getattr(getattr(c, 'subject', None), 'name', '')]
                # Scan for new/missing items on disk vs manifest
                try:
                    changes = scan_workspace_changes(base)
                except Exception:
                    changes = {'charts': {'new_on_disk': [], 'missing_on_disk': []}, 'subjects': {'new_on_disk': [], 'missing_on_disk': []}}
                imported = 0
                # Auto-import new charts found on disk
                try:
                    for fname in (changes.get('charts', {}).get('new_on_disk', []) or []):
                        path = str(Path(base) / 'charts' / fname)
                        try:
                            chart = import_chart_yaml(path)
                            add_or_update_chart(ws, chart, base_dir=base)
                            imported += 1
                        except Exception:
                            continue
                except Exception:
                    pass
                # Auto-import new subjects found on disk
                try:
                    for fname in (changes.get('subjects', {}).get('new_on_disk', []) or []):
                        path = str(Path(base) / 'subjects' / fname)
                        try:
                            data = read_yaml_file(path)
                            subj = ChartSubject(**data) if isinstance(data, dict) else None
                            if subj is not None:
                                add_subject(ws, subj, base_dir=base)
                                imported += 1
                        except Exception:
                            continue
                except Exception:
                    pass
                if imported:
                    try:
                        save_workspace_modular(ws, base)
                        self.show_message(f"Imported {imported} new item(s) from disk into workspace.")
                    except Exception:
                        pass
                # Notify about missing items (present in manifest, missing on disk)
                missing_ch = changes.get('charts', {}).get('missing_on_disk', []) if changes else []
                missing_sub = changes.get('subjects', {}).get('missing_on_disk', []) if changes else []
                if missing_ch or missing_sub:
                    msg_parts = []
                    if missing_ch:
                        msg_parts.append(f"{len(missing_ch)} chart(s) missing on disk")
                    if missing_sub:
                        msg_parts.append(f"{len(missing_sub)} subject(s) missing on disk")
                    self.show_message("Warning: " + ", ".join(msg_parts))
                # refresh names after sync
                names = [getattr(getattr(c, 'subject', None), 'name', '') for c in (ws.charts or []) if getattr(getattr(c, 'subject', None), 'name', '')]
                # Commit state only after success
                self.workspace_dir = base
                self.workspace = ws
                self.charts = names
                if self.charts:
                    self.current_person_index = 0
                    self.current_person_name = self.charts[0]
                else:
                    self.current_person_index = 0
                    self.current_person_name = ""
                self._update_person_buttons()
                # Focus first chart if any, so Export etc. work immediately
                try:
                    if self.charts:
                        self._focus_chart_by_name(self.charts[0])
                except Exception:
                    pass
                # render overview immediately
                self._render_workspace_overview(show_open_button=True)
            except Exception as e:
                self.show_message(f"Failed to load workspace: {e}")
            finally:
                popup.dismiss()

        # Wire buttons and open popup
        try:
            btn_cancel.bind(on_release=on_cancel)
            btn_select.bind(on_release=on_select)
        except Exception:
            pass
        try:
            popup.open()
        except Exception:
            pass

    def _popup_open_workspace(self):
        # Reuse the selection popup
        self._prompt_workspace_selection()

    def _popup_new_chart(self):
        # Legacy popup path no longer used; route to center Create view
        self.center_mode = "chart_create"
        self._render_chart_create_view()

    def _popup_open_chart(self):
        # Legacy popup path no longer used; route to center Open view
        self.center_mode = "open_view"
        self._render_open_chart_view()

    def _save_workspace(self):
        try:
            if getattr(self, "workspace", None) is not None and (self.workspace_dir or ""):
                save_workspace_modular(self.workspace, self.workspace_dir)
        except Exception as e:
            self.show_message(f"Failed to save workspace: {e}")

    def _popup_export_chart(self):
        # simple export of current chart YAML to chosen location
        if not self.chart:
            self.show_message("No chart to export")
            return
        box = BoxLayout(orientation='vertical', spacing=8, padding=8)
        box.add_widget(Label(text="Export current chart to folder", size_hint_y=None, height=28))
        chooser = FileChooserIconView(path=str(Path.cwd()), dirselect=True)
        box.add_widget(chooser)
        btns = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_cancel = self._md_button("Cancel", style="text", height=40)
        btn_export = self._md_button("Export", style="filled", height=40)
        btns.add_widget(btn_cancel)
        btns.add_widget(btn_export)
        box.add_widget(btns)
        popup = Popup(title="Export Chart", content=box, size_hint=(0.9, 0.9), auto_dismiss=False)

        def on_cancel(*_):
            popup.dismiss()

        def on_export(*_):
            dest = chooser.selection[0] if chooser.selection else chooser.path
            dest_p = Path(dest)
            if not dest_p.is_dir():
                dest_p = dest_p.parent
            try:
                data = self._chart_to_dict(self.chart)
                fname = f"{(getattr(self.chart, 'id', '') or 'chart').replace(' ', '-').lower()}.yml"
                out = dest_p / fname
                write_yaml_file(out, data, sort_keys=False, allow_unicode=True)
                self.show_message(f"Exported to {out}")
            except Exception as e:
                self.show_message(f"Failed to export: {e}")
            popup.dismiss()

        # Wire buttons and open popup
        try:
            btn_cancel.bind(on_release=on_cancel)
            btn_export.bind(on_release=on_export)
        except Exception:
            pass
        try:
            popup.open()
        except Exception:
            pass

    def _chart_to_dict(self, chart: ChartInstance) -> dict:
        # lightweight serialization for export
        from dataclasses import asdict, is_dataclass
        def conv(o):
            if is_dataclass(o):
                o = asdict(o)
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, list):
                return [conv(x) for x in o]
            from enum import Enum
            if isinstance(o, Enum):
                return o.value
            from datetime import datetime, date, time
            if isinstance(o, (datetime, date, time)):
                return o.isoformat()
            return o
        return conv(chart)

    # ---------- center overview renderer ----------
    def _render_workspace_overview(self, show_open_button: bool = False):
        ids = self.root.ids
        container = ids.get("chart_area")
        if not container:
            return
        container.clear_widgets()
        # show both side panes for generic overview
        self._set_side_panes(left=True, right=True)
        # Ensure left pane has no stacked items for this view
        self._wipe_left_content()
        # Title
        title = MDLabel(text=f"[b]{self.current_view_title} — Charts in Workspace[/b]", markup=True, size_hint_y=None, height=32, theme_text_color="Primary", halign="left")
        container.add_widget(title)
        # List of charts (clickable)
        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=6)
        grid.bind(minimum_height=grid.setter('height'))
        ws = getattr(self, 'workspace', None)
        if ws and ws.charts:
            for ch in ws.charts:
                info = summarize_chart(ch)
                name = info.get('name','')
                txt = f"• [b]{name}[/b] — {info.get('event_time','')} — {info.get('location',{}).get('name','')} (House {info.get('house_system','')}, Zodiac {info.get('zodiac_type','')})"
                btn = self._md_button(txt, style='text', height=32)
                btn.bind(on_release=lambda _b, nm=name: self._focus_chart_by_name(nm))
                grid.add_widget(btn)
        else:
            grid.add_widget(MDLabel(text="No charts in workspace.", size_hint_y=None, height=24, theme_text_color="Primary"))
        sv.add_widget(grid)
        container.add_widget(sv)
        # Button row
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        if show_open_button:
            btn_open = self._md_button("Open Chart (YAML)", style='filled', height=40)
            btn_open.bind(on_release=lambda *_: self._popup_open_chart())
            btn_row.add_widget(btn_open)
        container.add_widget(btn_row)

    def _focus_chart_by_name(self, name: str):
        """Switch context to an existing chart by subject name/id. Updates current_person and self.chart."""
        ws = getattr(self, 'workspace', None)
        if not ws or not ws.charts:
            return
        # Find matching chart via services
        found = find_chart_by_name_or_id(ws, name)
        if found is None:
            return
        # Update current state
        self.chart = found
        self.current_person_name = getattr(getattr(found, 'subject', None), 'name', name) or name
        try:
            if self.current_person_name not in (self.charts or []):
                self.charts = (self.charts or []) + [self.current_person_name]
            self.current_person_index = max(0, self.charts.index(self.current_person_name))
        except Exception:
            pass
        self._update_person_buttons()
        # Optionally update center title
        try:
            self.root.ids.get('view_label').text = f"[b]{self.current_view_title}[/b] — {self.current_person_name}"
        except Exception:
            pass
        self.show_message(f"Focused: {self.current_person_name}")

    # ---------- chart settings ----------
    def _render_chart_settings(self):
        """Render settings for the currently selected chart in the center area (top-aligned)."""
        ids = self.root.ids
        container = ids.get("chart_area")
        if not container:
            return
        container.clear_widgets()
        # for charAt settings keep three panes
        self._set_side_panes(left=True, right=True)
        # Ensure left pane shows the default two cards from KV (subject/time)
        self._show_left_defaults()
        # Add a small segmented selector in the left pane (mirrors Create Chart UX)
        try:
            left = ids.get('left_col')
            if left:
                selector = BoxLayout(orientation='vertical', size_hint_y=None, spacing=6)
                selector.bind(minimum_height=selector.setter('height'))
                items = [
                    ("Chart options", "chart"),
                    ("Transit options", "transits"),
                ]
                buttons = []

                def _show_container(widget, show: bool):
                    try:
                        if widget is None:
                            return
                        widget.disabled = not show
                        widget.opacity = 1 if show else 0
                        # enforce vertical sizing visibility
                        if show:
                            # prefer natural minimum height if available
                            h = getattr(widget, 'minimum_height', None)
                            if h is None or not h:
                                h = getattr(widget, 'height', 0) or 1
                            widget.size_hint_y = None
                            widget.height = max(1, h)
                        else:
                            widget.size_hint_y = None
                            widget.height = 0
                    except Exception:
                        pass

                def _ensure_open(section_key: str):
                    # section_key in {'subject','time','transits'}
                    try:
                        if section_key == 'subject':
                            content = ids.get('subject_content')
                        elif section_key == 'time':
                            content = ids.get('time_content')
                        else:
                            content = ids.get('transits_content')
                        if content is not None and (getattr(content, 'height', 0) or 0) <= 1:
                            self.toggle_section(section_key)
                    except Exception:
                        pass

                def _ensure_closed(section_key: str):
                    try:
                        if section_key == 'subject':
                            content = ids.get('subject_content')
                        elif section_key == 'time':
                            content = ids.get('time_content')
                        else:
                            content = ids.get('transits_content')
                        if content is not None and (getattr(content, 'height', 0) or 0) > 1:
                            self.toggle_section(section_key)
                    except Exception:
                        pass

                def set_mode(which):
                    # Update visual state of buttons
                    for btn, key in buttons:
                        try:
                            btn.style = 'filled' if key == which else 'text'
                        except Exception:
                            pass
                    # Toggle whole-card visibility to avoid residuals
                    chart_cards = ids.get('chart_cards')
                    transits_card = ids.get('transits_card')
                    if which == 'chart':
                        _show_container(chart_cards, True)
                        _show_container(transits_card, False)
                        # ensure inner sections are open/closed accordingly
                        _ensure_open('subject')
                        _ensure_open('time')
                        _ensure_closed('transits')
                    else:
                        _show_container(chart_cards, False)
                        _show_container(transits_card, True)
                        _ensure_closed('subject')
                        _ensure_closed('time')
                        _ensure_open('transits')

                # Build selector buttons
                from kivymd.uix.button import MDButton, MDButtonText
                for label, key in items:
                    btn = MDButton(style=('filled' if key == 'chart' else 'text'), size_hint_y=None, height=36)
                    btn.add_widget(MDButtonText(text=label))
                    btn.bind(on_release=lambda _inst, k=key: set_mode(k))
                    buttons.append((btn, key))
                    selector.add_widget(btn)

                # Place selector at the top of the left pane
                try:
                    left.add_widget(selector)
                except Exception:
                    pass

                # Initialize default mode to 'chart'
                set_mode('chart')
        except Exception:
            pass
        root = AnchorLayout(anchor_y='top')
        vbox = BoxLayout(orientation='vertical', size_hint_y=None)
        vbox.bind(minimum_height=vbox.setter('height'))
        title = MDLabel(text=f"[b]Chart Settings[/b] — {self.current_person_name or ''}", markup=True, size_hint_y=None, height=32, theme_text_color="Primary", halign="left")
        vbox.add_widget(title)
        grid = GridLayout(cols=2, spacing=8, size_hint_y=None, padding=8)
        grid.bind(minimum_height=grid.setter('height'))
        ch = getattr(self, 'chart', None)
        def add_row(k, v):
            grid.add_widget(MDLabel(text=str(k), size_hint_y=None, height=26, theme_text_color="Primary"))
            grid.add_widget(MDLabel(text=str(v), size_hint_y=None, height=26, theme_text_color="Primary"))
        if not ch:
            add_row("Info", "No chart built yet")
        else:
            cfg = getattr(ch, 'config', None)
            subj = getattr(ch, 'subject', None)
            add_row("Name", getattr(subj, 'name', ''))
            add_row("Event time", getattr(subj, 'event_time', ''))
            loc = getattr(subj, 'location', None)
            add_row("Location", getattr(loc, 'name', '') if loc else '')
            add_row("Engine", getattr(cfg, 'engine', ''))
            add_row("House system", getattr(cfg, 'house_system', ''))
            add_row("Zodiac", getattr(cfg, 'zodiac_type', ''))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(grid)
        vbox.add_widget(sv)
        root.add_widget(vbox)
        container.add_widget(root)

    # ---------- Chart creation center view ----------
    def _render_chart_create_view(self):
        ids = self.root.ids
        container = ids.get("chart_area")
        if not container:
            return
        container.clear_widgets()
        # Layout: left has chart type selector, center has form, right hidden per spec
        self._set_side_panes(left=True, right=False)
        # Clear left pane to avoid stacking previous widgets
        self._wipe_left_content()
        # Title
        title = MDLabel(text=f"[b]Create Chart[/b]", markup=True, size_hint_y=None, height=32, theme_text_color="Primary", halign="left")
        container.add_widget(title)
        # Left selector (place into left_col top):
        left = ids.get('left_col')
        if left:
            # Add a small selector COLUMN using MDButtons to simulate segmented control (top-aligned)
            selector = BoxLayout(orientation='vertical', size_hint_y=None, spacing=6)
            selector.bind(minimum_height=selector.setter('height'))
            items = [
                ("Nativity", "NATAL"),
                ("Event", "EVENT"),
                ("Horary", "HORARY"),
            ]
            buttons = []
            def set_mode(mode):
                self.chart_type = mode
                # update visual selection by switching button styles
                for btn, m in buttons:
                    try:
                        btn.style = 'filled' if m == mode else 'text'
                    except Exception:
                        pass
            selector.clear_widgets()
            for label, mode in items:
                btn = self._md_button(label, style=('filled' if self.chart_type == mode else 'text'), height=36)
                btn.bind(on_release=lambda inst, m=mode: set_mode(m))
                buttons.append((btn, mode))
                selector.add_widget(btn)
            # ensure only this widget exists in left pane
            try:
                left.add_widget(selector)
            except Exception:
                pass
        # Center form
        form = GridLayout(cols=2, spacing=8, size_hint_y=None, padding=8)
        form.bind(minimum_height=form.setter('height'))
        def add_row(lbl, widget):
            form.add_widget(MDLabel(text=lbl, size_hint_y=None, height=28, theme_text_color="Primary"))
            form.add_widget(widget)
        name_inp = TextInput(hint_text="Name", multiline=False)
        date_inp = TextInput(hint_text="Date YYYY-MM-DD", multiline=False)
        time_inp = TextInput(hint_text="Time HH:MM", multiline=False)
        place_inp = TextInput(hint_text="Place (e.g., Prague)", multiline=False)
        tags_inp = TextInput(hint_text="Tags (comma separated)", multiline=False)
        add_row("Name", name_inp)
        add_row("Date", date_inp)
        add_row("Time", time_inp)
        add_row("Place", place_inp)
        add_row("Tags", tags_inp)
        # Advanced options expander (placeholder content)
        adv_open = False
        adv_btn = self._md_button('Advanced settings', style='text', height=32)
        adv_box = BoxLayout(orientation='vertical', size_hint_y=None, height=0, opacity=0)
        adv_box.add_widget(MDLabel(text='Lorem ipsum dolor sit amet...', size_hint_y=None, height=24, theme_text_color="Primary"))
        def _toggle_adv(*_):
            nonlocal adv_open
            adv_open = not adv_open
            if adv_open:
                adv_box.height = 100
                adv_box.opacity = 1
                try:
                    adv_btn.style = 'filled'
                except Exception:
                    pass
            else:
                adv_box.height = 0
                adv_box.opacity = 0
                try:
                    adv_btn.style = 'text'
                except Exception:
                    pass
        adv_btn.bind(on_release=_toggle_adv)
        # span full width: add empty placeholder for first column
        form.add_widget(MDLabel(text=''))
        form.add_widget(adv_btn)
        form.add_widget(MDLabel(text=''))
        form.add_widget(adv_box)
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_create = self._md_button("Create", style="filled", height=40)
        btn_row.add_widget(btn_create)
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(form)
        container.add_widget(sv)
        container.add_widget(btn_row)
        def on_create(*_):
            nm = (name_inp.text or '').strip()
            ds = (date_inp.text or '').strip()
            ts = (time_inp.text or '').strip()
            pl = (place_inp.text or 'Prague').strip() or 'Prague'
            tags = [t.strip() for t in (tags_inp.text or '').split(',') if t.strip()]
            if not nm:
                self.show_message('Name is required')
                return
            # Duplicate check by name
            existing_names = [getattr(getattr(c, 'subject', None), 'name', None) for c in (getattr(self, 'workspace', None).charts or [])]
            if nm in existing_names:
                self._focus_chart_by_name(nm)
                self.show_message('Chart already exists — focused existing')
                return
            dt_str = f"{ds} {ts}" if ds and ts else ds or now_utc().strftime("%Y-%m-%d %H:%M")
            mode = ChartMode[self.chart_type]
            self.build_chart(nm, dt_str, pl, mode=mode, tags=tags)
            try:
                add_or_update_chart(self.workspace, self.chart, base_dir=self.workspace_dir)
                self._save_workspace()
                # update charts chips from workspace to keep in sync
                try:
                    ws = getattr(self, 'workspace', None)
                    self.charts = [getattr(getattr(c, 'subject', None), 'name', '') for c in (ws.charts or []) if getattr(getattr(c, 'subject', None), 'name', '')]
                except Exception:
                    # fallback append-only
                    names = self.charts or []
                    if nm not in names:
                        names.append(nm)
                    self.charts = names
                self.current_person_name = nm
                self.current_person_index = max(0, self.charts.index(nm))
                self._update_person_buttons()
                self.show_message('Chart created')
            except Exception as e:
                self.show_message(f'Failed to save chart: {e}')
        btn_create.bind(on_release=on_create)

    # ---------- Open chart view ----------
    def _render_open_chart_view(self):
        ids = self.root.ids
        container = ids.get("chart_area")
        if not container:
            return
        container.clear_widgets()
        # Per spec: left shows options, center search+list, right hidden
        self._set_side_panes(left=True, right=False)
        # Left options
        left = ids.get('left_col')
        if left:
            # Clear any previous items in left pane
            self._wipe_left_content()
            opt_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=6)
            btn_my = self._md_button('My Horoscopes', style='text', height=36)
            btn_db = self._md_button('Persons Database', style='text', height=36)
            opt_box.add_widget(btn_my)
            opt_box.add_widget(btn_db)
            try:
                left.add_widget(opt_box)
            except Exception:
                pass
        # Center: search + list
        search_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        search_inp = TextInput(hint_text='Search...')
        btn_new = self._md_button('Import Chart (YAML)', style='filled', height=40)
        search_row.add_widget(search_inp)
        search_row.add_widget(btn_new)
        container.add_widget(search_row)
        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=6)
        grid.bind(minimum_height=grid.setter('height'))
        ws = getattr(self, 'workspace', None)
        self._open_view_items = []
        self._open_view_rows = list_open_view_rows(ws) if ws else []
        def _render_rows(rows):
            # Clear existing rows except header (first child)
            # Remove everything and re-add header for simplicity
            grid.clear_widgets()
            header = GridLayout(cols=4, size_hint_y=None, height=28, spacing=6)
            header.add_widget(MDLabel(text='[b]Name[/b]', markup=True, theme_text_color="Primary"))
            header.add_widget(MDLabel(text='[b]Event time[/b]', markup=True, theme_text_color="Primary"))
            header.add_widget(MDLabel(text='[b]Location[/b]', markup=True, theme_text_color="Primary"))
            header.add_widget(MDLabel(text='[b]Tags[/b]', markup=True, theme_text_color="Primary"))
            grid.add_widget(header)
            self._open_view_items = []
            for info in rows:
                name = info.get('name', '')
                event_time = info.get('event_time', '')
                # Fallback to workspace default location if per-chart missing
                try:
                    ws = getattr(self, 'workspace', None)
                    dl = getattr(getattr(ws, 'default_location', None), 'name', '') if ws else ''
                except Exception:
                    dl = ''
                location_name = info.get('location', '') or dl
                tags = info.get('tags', '')
                row = GridLayout(cols=4, size_hint_y=None, height=32, spacing=6)
                btn_name = self._md_button(name or '-', style='text', height=32)
                btn_name.bind(on_release=lambda _b, nm=name: self._focus_chart_by_name(nm))
                row.add_widget(btn_name)
                row.add_widget(MDLabel(text=str(event_time), theme_text_color="Primary"))
                row.add_widget(MDLabel(text=str(location_name), theme_text_color="Primary"))
                row.add_widget(MDLabel(text=str(tags), theme_text_color="Primary"))
                row._search_text = info.get('search_text', '').lower()
                grid.add_widget(row)
                self._open_view_items.append(row)
        _render_rows(self._open_view_rows)
        sv.add_widget(grid)
        container.add_widget(sv)
        # Wire buttons
        btn_new.bind(on_release=lambda *_: self._popup_import_chart())
        def _apply_filter(instance, value):
            q = (value or '').lower().strip()
            if not q:
                _render_rows(self._open_view_rows)
                return
            filtered = [r for r in self._open_view_rows if q in r.get('search_text','')]
            _render_rows(filtered)
        search_inp.bind(text=_apply_filter)

    def _popup_import_chart(self):
        # Popup to import a single chart YAML into current workspace
        if not self._ensure_workspace_selected():
            return
        box = BoxLayout(orientation='vertical', spacing=8, padding=8)
        box.add_widget(MDLabel(text="Select a chart YAML file to import", size_hint_y=None, height=28, theme_text_color="Primary"))
        chooser = FileChooserIconView(path=self.workspace_dir or str(Path.cwd()))
        box.add_widget(chooser)
        btns = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_cancel = self._md_button("Cancel", style="text", height=40)
        btn_import = self._md_button("Import", style="filled", height=40)
        btns.add_widget(btn_cancel)
        btns.add_widget(btn_import)
        box.add_widget(btns)
        popup = Popup(title="Import Chart", content=box, size_hint=(0.9, 0.9), auto_dismiss=False)

        def on_cancel(*_):
            popup.dismiss()

        def on_import(*_):
            try:
                sel = chooser.selection[0] if chooser.selection else chooser.path
                if not sel or not Path(sel).is_file():
                    self.show_message('Please select a YAML file')
                    return
                chart = import_chart_yaml(sel)
                add_or_update_chart(self.workspace, chart, base_dir=self.workspace_dir)
                # update UI chips and focus
                nm = getattr(getattr(chart, 'subject', None), 'name', getattr(chart, 'id', 'chart')) or getattr(chart, 'id', 'chart')
                # rebuild charts list from workspace to ensure sync
                try:
                    ws = getattr(self, 'workspace', None)
                    self.charts = [getattr(getattr(c, 'subject', None), 'name', '') for c in (ws.charts or []) if getattr(getattr(c, 'subject', None), 'name', '')]
                except Exception:
                    # fallback append-only
                    names = self.charts or []
                    if nm not in names:
                        names.append(nm)
                    self.charts = names
                self.current_person_name = nm
                try:
                    self.current_person_index = max(0, self.charts.index(nm))
                except Exception:
                    pass
                self._update_person_buttons()
                self.show_message('Chart imported')
                # Refresh open-view list to include the new item
                self._render_open_chart_view()
            except Exception as e:
                self.show_message(f"Failed to import chart: {e}")
            finally:
                popup.dismiss()

        # Wire buttons and open popup
        try:
            btn_cancel.bind(on_release=on_cancel)
            btn_import.bind(on_release=on_import)
        except Exception:
            pass
        try:
            popup.open()
        except Exception:
            pass

    # ---------- helper for side panes ----------
    def _set_side_panes(self, left: bool, right: bool):
        ids = self.root.ids
        lcol = ids.get('left_col')
        rcol = ids.get('right_col')
        mcol = ids.get('middle_col')
        # Left: 20% when visible
        if lcol:
            lcol.size_hint_x = 0.20 if left else 0
            lcol.opacity = 1 if left else 0
            lcol.disabled = not left
        # Right: 20% when visible
        if rcol:
            rcol.size_hint_x = 0.20 if right else 0
            rcol.opacity = 1 if right else 0
            rcol.disabled = not right
        # Middle: 60% for three columns, 80% for two columns, 100% for single
        if mcol:
            if left and right:
                mcol.size_hint_x = 0.60
            elif left or right:
                mcol.size_hint_x = 0.80
            else:
                mcol.size_hint_x = 1.0

    def _wipe_left_content(self):
        """Remove all widgets from the left pane to prevent stacking between views."""
        try:
            left = self.root.ids.get('left_col')
            if left:
                left.clear_widgets()
        except Exception:
            pass

    def _show_left_defaults(self):
        """Restore the default KV-defined left widgets (subject/time cards)."""
        try:
            left = self.root.ids.get('left_col')
            if left is None:
                return
            left.clear_widgets()
            if getattr(self, '_left_defaults', None):
                for w in reversed(self._left_defaults):
                    left.add_widget(w)
        except Exception:
            pass

    def _render_settings_view(self):
        ids = self.root.ids
        container = ids.get("chart_area")
        if not container:
            return
        container.clear_widgets()
        # Settings layout: left categories, center controls; hide right pane per spec
        self._set_side_panes(left=True, right=False)
        # Left categories
        self._wipe_left_content()
        left = ids.get('left_col')
        cats = BoxLayout(orientation='vertical', spacing=6, size_hint_y=None)
        cats.bind(minimum_height=cats.setter('height'))
        cat_buttons = []
        def add_cat(label):
            b = self._md_button(label, style='text', height=36)
            cat_buttons.append(b)
            cats.add_widget(b)
            return b
        btn_general = add_cat('General')
        btn_ephem = add_cat('Ephemeris')
        btn_appearance = add_cat('Appearance')
        try:
            left.add_widget(cats)
        except Exception:
            pass
        # Center controls (default: General)
        ws = getattr(self, 'workspace', None)
        center_box = BoxLayout(orientation='vertical', spacing=8)
        form = GridLayout(cols=2, spacing=8, size_hint_y=None, padding=8)
        form.bind(minimum_height=form.setter('height'))
        def row(lbl, widget):
            form.add_widget(MDLabel(text=lbl, size_hint_y=None, height=28, theme_text_color="Primary"))
            form.add_widget(widget)
        # General settings
        loc_inp = TextInput(text=(getattr(getattr(ws,'default_location',None),'name','') if ws else ''), hint_text='Default location')
        aspects_inp = TextInput(text=", ".join(getattr(ws,'default_aspects',[]) or []), hint_text='aspects ids, comma separated')

        # Dropdown selectors (MD) for House, Theme, Engine
        house_options = [h for h in getattr(HouseSystem, '__members__', {}).keys()] or ['PLACIDUS']
        engine_options = [e for e in getattr(EngineType,'__members__',{}).keys()] or ['JPL']
        theme_options = ['default','dark','light']

        house_val = str(getattr(ws,'default_house_system','PLACIDUS') or 'PLACIDUS')
        engine_val = str(getattr(getattr(ws,'default',None),'ephemeris_engine','SWISSEPH') or 'SWISSEPH')
        theme_val = str(getattr(ws,'color_theme','default') or 'default')

        house_btn = self._md_button(house_val, style='tonal', height=36)
        engine_btn = self._md_button(engine_val, style='tonal', height=36)
        theme_btn = self._md_button(theme_val, style='tonal', height=36)

        def _set_house(v):
            nonlocal house_val
            house_val = str(v)
            try:
                # update button label
                house_btn.children[0].text = house_val
            except Exception:
                pass
            try:
                house_menu.dismiss()
            except Exception:
                pass

        def _set_engine(v):
            nonlocal engine_val
            engine_val = str(v)
            try:
                engine_btn.children[0].text = engine_val
            except Exception:
                pass
            try:
                engine_menu.dismiss()
            except Exception:
                pass

        def _set_theme(v):
            nonlocal theme_val
            theme_val = str(v)
            try:
                theme_btn.children[0].text = theme_val
            except Exception:
                pass
            try:
                theme_menu.dismiss()
            except Exception:
                pass

        house_menu = MDDropdownMenu(
            caller=house_btn,
            items=[{"text": opt, "on_release": (lambda v=opt: _set_house(v))} for opt in house_options],
        )
        engine_menu = MDDropdownMenu(
            caller=engine_btn,
            items=[{"text": opt, "on_release": (lambda v=opt: _set_engine(v))} for opt in engine_options],
        )
        theme_menu = MDDropdownMenu(
            caller=theme_btn,
            items=[{"text": opt, "on_release": (lambda v=opt: _set_theme(v))} for opt in theme_options],
        )

        house_btn.bind(on_release=lambda *_: house_menu.open())
        engine_btn.bind(on_release=lambda *_: engine_menu.open())
        theme_btn.bind(on_release=lambda *_: theme_menu.open())

        row('Default location', loc_inp)
        row('House system', house_btn)
        row('Default aspects', aspects_inp)
        row('Theme', theme_btn)
        row('Default engine', engine_btn)
        save_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        btn_save = self._md_button('Save Settings', style='filled', height=48)
        save_row.add_widget(btn_save)
        center_box.add_widget(form)
        center_box.add_widget(save_row)
        container.add_widget(center_box)
        def _select_cat(which):
            # For now, we keep a single form; categories are placeholders to grow later
            pass
        btn_general.bind(on_release=lambda *_: _select_cat('general'))
        btn_ephem.bind(on_release=lambda *_: _select_cat('ephemeris'))
        btn_appearance.bind(on_release=lambda *_: _select_cat('appearance'))
        def _save_settings(*_):
            try:
                if ws is None:
                    self.show_message('No workspace loaded')
                    return
                # Apply
                dl = (loc_inp.text or '').strip()
                if dl:
                    try:
                        loc = Actual(dl, t='loc').to_model_location()
                        ws.default_location = loc
                    except Exception:
                        pass
                try:
                    hs_key = (house_val or 'PLACIDUS').upper()
                    ws.default_house_system = getattr(HouseSystem, hs_key, HouseSystem.PLACIDUS)
                except Exception:
                    ws.default_house_system = HouseSystem.PLACIDUS
                ws.default_aspects = [a.strip() for a in (aspects_inp.text or '').split(',') if a.strip()]
                ws.color_theme = theme_val or 'default'
                try:
                    eng_key = (engine_val or 'SWISSEPH').upper()
                    ws.default.ephemeris_engine = getattr(EngineType, eng_key, EngineType.SWISSEPH)
                except Exception:
                    pass
                save_workspace_modular(ws, self.workspace_dir)
                self.show_message('Settings saved')
            except Exception as e:
                self.show_message(f'Failed to save settings: {e}')
        btn_save.bind(on_release=_save_settings)

    # ---------- dialogs ----------
    def show_message(self, message: str):
        try:
            bar = MDSnackbar(
                MDSnackbarText(text=str(message)),
                y=24,
                pos_hint={"center_x": 0.5},
                size_hint_x=0.9,
                md_bg_color=self.theme_cls.primary_color,
            )
            bar.open()
        except Exception:
            # Fallback: print to console
            print(f"INFO: {message}")

    def close_dialog(self, *_):
        # No-op for snackbar path; kept for backward compatibility
        pass

    def _md_button(self, text: str, style: str = "text", height: int = 36):
        """Factory to create MDButton with text and consistent sizing for light theme."""
        btn = MDButton(style=style, size_hint_y=None, height=height)
        btn.add_widget(MDButtonText(text=text))
        return btn

if __name__ == '__main__':
    MyApp().run()
