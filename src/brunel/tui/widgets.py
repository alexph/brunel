from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable

from brunel.protocol import ProjectView


class ProjectTable(DataTable):
    """Show registered projects and open the selected row."""

    class OpenProject(Message):
        def __init__(self, project: ProjectView):
            super().__init__()
            self.project = project

    def __init__(self, **kwargs):
        super().__init__(cursor_type="row", zebra_stripes=True, **kwargs)
        self.projects: dict[str, ProjectView] = {}
        self.add_columns("Project", "Directory")

    def set_projects(self, projects: list[ProjectView]) -> None:
        selected = None
        if self.row_count:
            selected = self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value
        self.clear()
        self.projects = {str(project.id): project for project in projects}
        for index, project in enumerate(projects):
            self.add_row(Text(project.name), Text(project.location), key=str(project.id))
            if str(project.id) == selected:
                self.move_cursor(row=index)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        project = self.projects.get(event.row_key.value)
        if project is not None:
            self.post_message(self.OpenProject(project))
