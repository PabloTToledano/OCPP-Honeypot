from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OCPPVariables:
    variables = {"BasicAuthPassword": "password", "NetworkConfigurationPriority": []}
