from textual.app import App, ComposeResult
from textual.containers import Container, VerticalGroup
from textual.widgets import Header, Footer, Static, OptionList, Tree
from textual.widgets.option_list import Option

import subprocess
import json
from pathlib import Path


class FileTree(Tree):
    BORDER_TITLE = "Projects"
    BINDINGS = [("j", "cursor_down", "Down"), ("k", "cursor_up", "Up")]
    can_focus = True

    def on_mount(self) -> None:
        target_dir = Path.home() / "Code"
        for item in target_dir.iterdir():
            if item.is_dir():
                self.root.add_leaf(item.name)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        selected_node = event.node
        dir_name = str(selected_node.label)
        path_to_project = Path.home() / "Code" / dir_name
        nvim_command = f"cd  {path_to_project} && nvim"
        session_name = dir_name.replace(" ", "-")

        # Build the final tmux command
        tmux_command = [
            "tmux",
            "new-session",
            "-d",  # -d: Run in detached mode (in the background)
            "-s",
            session_name,  # -s: Name the session
            nvim_command,  # The command to run inside the new session
        ]

        # Run the command
        try:
            subprocess.run(tmux_command, check=True)
            # Log success to the debug console
            self.log(f"Successfully launched tmux session '{session_name}'")
        except Exception as e:
            # Log any errors
            self.log(f"Error launching tmux: {e}")
        # Switch to the session.
        # This will only work if you ran Janus from *inside* tmux.
        # This command will also cause the Janus app to exit.
        try:
            # We don't use 'check=True' here, as it might
            # exit before the app can even register it.
            subprocess.run(["tmux", "switch-client", "-t", session_name])
        except Exception as e:
            # This log probably won't be seen, but it's good practice.
            self.log(f"Error switching client: {e}")


class Notes(VerticalGroup):
    BORDER_TITLE = "Notes"
    can_focus = True
    pass


class Weather(VerticalGroup):
    BORDER_TITLE = "Weather"
    pass


class SubwayStats(VerticalGroup):
    BORDER_TITLE = "Subway Stats"
    can_focus = True
    pass


class SSH(OptionList):
    BORDER_TITLE = "SSH"
    BINDINGS = [("j", "cursor_down", "Down"), ("k", "cursor_up", "Up")]
    can_focus = True

    def on_mount(self) -> None:
        """Populate the OptionList with our target names."""
        # 1. Read the config.ini file
        config = configparser.ConfigParser()
        config.read("config.ini")

        # 2. Check if the [SSH] section exists and load it
        if "SSH" in config:
            self.ssh_targets = dict(config["SSH"])

        # 3. Populate the OptionList from our new dictionary
        for name in self.ssh_targets:
            self.add_option(
                Option(name, id=name)
            )  # Add each *key* (the display name) from our dictionary
        for name in self.SSH_TARGETS:
            self.add_option(Option(name, id=name))  # Use id for safety

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Called when the user presses enter on an option."""

        # 1. Get the display name from the selected option's ID
        selected_name = event.option.id

        if not selected_name:
            self.log("Error: Selected Option has no ID")
            return

        # 2. Look up the corresponding command target from our dictionary
        ssh_target = self.SSH_TARGETS.get(selected_name)

        if not ssh_target:
            self.log(f"Error: No target found for {selected_name}")
            return

        # 3. Define the shell command to run
        # We'll name the tmux session the same as the selected name
        session_name = selected_name.replace(" ", "_")  # Tmux doesn't like spaces

        # This is the command that will run in the new tmux session
        ssh_command = f"ssh {ssh_target}"

        # 4. Build the final tmux command
        tmux_command = [
            "tmux",
            "new-session",
            "-d",  # -d: Run in detached mode (in the background)
            "-s",
            session_name,  # -s: Name the session
            ssh_command,  # The command to run inside the new session
        ]

        # 5. Run the command
        try:
            subprocess.run(tmux_command, check=True)
            # Log success to the debug console
            self.log(f"Successfully launched tmux session '{session_name}'")
        except Exception as e:
            # Log any errors
            self.log(f"Error launching tmux: {e}")
        # 3. Switch to the session.
        # This will only work if you ran Janus from *inside* tmux.
        # This command will also cause the Janus app to exit.
        try:
            # We don't use 'check=True' here, as it might
            # exit before the app can even register it.
            subprocess.run(["tmux", "switch-client", "-t", session_name])
        except Exception as e:
            # This log probably won't be seen, but it's good practice.
            self.log(f"Error switching client: {e}")


class SysInfo(VerticalGroup):
    BORDER_TITLE = "System Info"
    """A widget to display system information."""

    # 1. This is our worker, a regular (non-async) function
    def update_sys_info(self) -> None:
        """Worker to fetch sys info and update widgets."""

        command = ["lua", "scripts/get_sys_info.lua"]
        try:
            # This is a blocking call
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            # Find our child widgets
            battery_pane = self.query_one("#batteryinfo", Static)
            mem_pane = self.query_one("#meminfo", Static)

            # Update them
            if "battery" in data:
                battery_pane.update(f"Battery: {data['battery']}%")
            if "memory" in data:
                mem_pane.update(f"Memory: {data['memory']}")

        except Exception as e:
            # Handle errors
            battery_pane = self.query_one("#batteryinfo", Static)
            battery_pane.update(f"Sys Info: {e}")

    # 2. This runs when the widget is mounted
    def on_mount(self) -> None:
        """Start a timer to update sys info."""
        # Run the worker once, *in a thread*
        self.run_worker(self.update_sys_info, thread=True, exclusive=True)

        # Set an interval to call our helper method
        self.set_interval(3, self.run_sys_info_worker)

    # 3. This helper is called by the timer
    def run_sys_info_worker(self) -> None:
        """Helper to run the worker from the timer."""
        # We must also run this in a thread
        self.run_worker(self.update_sys_info, thread=True, exclusive=True)

    # 4. The compose method
    def compose(self) -> ComposeResult:
        """Create child widgets of the sys info pane."""
        yield Static("Loading...", id="batteryinfo")
        yield Static("", id="meminfo")


class JanusApp(App):
    """A simple TUI Dashboard"""

    CSS_PATH = "main.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle Dark Mode"),
        ("q", "quit", "Quit App"),
    ]

    def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app"""
        yield Header()
        yield Footer()

        with Container(id="main"):
            yield Notes(id="notes", classes="pane")
            yield FileTree("Projects", id="file_tree", classes="pane")

        with Container(id="sidebar"):
            yield Weather(id="weather", classes="pane")
            yield SubwayStats(id="subway", classes="pane")
            yield SSH(id="ssh", classes="pane")
            yield SysInfo(id="sys_info", classes="pane")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "catppuccin-mocha"
            if self.theme == "catppuccin-latte"
            else "catppuccin-latte"
        )


if __name__ == "__main__":
    app = JanusApp()
    app.run()
