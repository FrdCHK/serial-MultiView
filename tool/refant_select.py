"""
select refant from included antennas
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import sys


def refant_select(ant_table):
    pt = ant_table.loc[ant_table["NAME"] == "PT", "ID"]
    la = ant_table.loc[ant_table["NAME"] == "LA", "ID"]
    kp = ant_table.loc[ant_table["NAME"] == "KP", "ID"]
    fd = ant_table.loc[ant_table["NAME"] == "FD", "ID"]
    if not pt.empty:
        return pt.values[0]
    elif not la.empty:
        return la.values[0]
    elif not kp.empty:
        return kp.values[0]
    elif not fd.empty:
        return fd.values[0]
    else:
        print("\033[31mNo valid refant found!\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    pass
