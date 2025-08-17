from textual.app import ComposeResult, App
from textual.containers import Vertical
from textual.widgets import Button, OptionList, Select, Static


class ProjectSelection(App):
    def __init__(self, options: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = ''
        self.options = options

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static('Project Selection'),
            OptionList(
                *self.options
            )
        )
    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
            """
            Handle OptionList selection: store the selected value and quit the app.
            """
            # event.option is the Option object selected
            self.result = str(event.option.prompt)
            # gracefully stop the app
            await self.action_quit()
