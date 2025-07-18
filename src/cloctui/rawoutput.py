# This is for seeing the raw JSON output in the console
# For testing and debugging purposes

import json
from cloctui.main import CLOC, ClocJsonResult

if __name__ == "__main__":

    timeout = 15
    working_directory = "./"
    dir_to_scan = "src"

    result: ClocJsonResult = json.loads(
        CLOC()
        .add_flag("--by-file")
        .add_flag("--json")
        .add_option("--timeout", timeout)
        .set_working_directory(working_directory)
        .add_argument(dir_to_scan)
        .execute()
    )
    print(json.dumps(result, indent=4))
