from enum import Enum


class ImageType(Enum):
    UBUNTU_24_10_X64 = "ubuntu-24-10-x64"
    UBUNTU_20_04_X64 = "ubuntu-20-04-x64"


class Region(Enum):
    NYC_1 = "nyc1"
    AMSTERDAM_3 = "ams3"


class MachineSize(Enum):
    """Anything with C_* is a CPU optimized machine with 10GbE network."""

    S_1VCPU_512MB_10GB = "s-1vcpu-512mb-10gb"
    S_1VCPU_1GB = "s-1vcpu-1gb"
    S_1VCPU_1GB_AMD = "s-1vcpu-1gb-amd"
    S_1VCPU_1GB_INTEL = "s-1vcpu-1gb-intel"
    S_1VCPU_1GB_35GB_INTEL = "s-1vcpu-1gb-35gb-intel"
    S_1VCPU_2GB = "s-1vcpu-2gb"
    S_1VCPU_2GB_AMD = "s-1vcpu-2gb-amd"
    S_1VCPU_2GB_INTEL = "s-1vcpu-2gb-intel"
    S_1VCPU_2GB_70GB_INTEL = "s-1vcpu-2gb-70gb-intel"
    S_2VCPU_2GB = "s-2vcpu-2gb"
    S_2VCPU_2GB_AMD = "s-2vcpu-2gb-amd"
    S_2VCPU_2GB_INTEL = "s-2vcpu-2gb-intel"
    S_2VCPU_2GB_90GB_INTEL = "s-2vcpu-2gb-90gb-intel"
    S_2VCPU_4GB = "s-2vcpu-4gb"
    S_2VCPU_4GB_AMD = "s-2vcpu-4gb-amd"
    S_2VCPU_4GB_INTEL = "s-2vcpu-4gb-intel"
    S_2VCPU_4GB_120GB_INTEL = "s-2vcpu-4gb-120gb-intel"
    S_2VCPU_8GB_AMD = "s-2vcpu-8gb-amd"
    C_2 = "c-2"
    C2_2VCPU_4GB = "c2-2vcpu-4gb"
    S_2VCPU_8GB_160GB_INTEL = "s-2vcpu-8gb-160gb-intel"
    S_4VCPU_8GB = "s-4vcpu-8gb"
    S_4VCPU_8GB_AMD = "s-4vcpu-8gb-amd"
    S_4VCPU_8GB_INTEL = "s-4vcpu-8gb-intel"
    G_2VCPU_8GB = "g-2vcpu-8gb"
    S_4VCPU_8GB_240GB_INTEL = "s-4vcpu-8gb-240gb-intel"
    GD_2VCPU_8GB = "gd-2vcpu-8gb"
    G_2VCPU_8GB_INTEL = "g-2vcpu-8gb-intel"
    GD_2VCPU_8GB_INTEL = "gd-2vcpu-8gb-intel"
    S_4VCPU_16GB_AMD = "s-4vcpu-16gb-amd"
    M_2VCPU_16GB = "m-2vcpu-16gb"
    C_4 = "c-4"
    C2_4VCPU_8GB = "c2-4vcpu-8gb"
    S_4VCPU_16GB_320GB_INTEL = "s-4vcpu-16gb-320gb-intel"
    S_8VCPU_16GB = "s-8vcpu-16gb"
    M_2VCPU_16GB_INTEL = "m-2vcpu-16gb-intel"
    M3_2VCPU_16GB = "m3-2vcpu-16gb"
    C_4_INTEL = "c-4-intel"
    M3_2VCPU_16GB_INTEL = "m3-2vcpu-16gb-intel"
    S_8VCPU_16GB_AMD = "s-8vcpu-16gb-amd"
    S_8VCPU_16GB_INTEL = "s-8vcpu-16gb-intel"
    C2_4VCPU_8GB_INTEL = "c2-4vcpu-8gb-intel"
    G_4VCPU_16GB = "g-4vcpu-16gb"
    S_8VCPU_16GB_480GB_INTEL = "s-8vcpu-16gb-480gb-intel"
    SO_2VCPU_16GB_INTEL = "so-2vcpu-16gb-intel"
    SO_2VCPU_16GB = "so-2vcpu-16gb"
    M6_2VCPU_16GB = "m6-2vcpu-16gb"
    GD_4VCPU_16GB = "gd-4vcpu-16gb"
    SO1_5_2VCPU_16GB_INTEL = "so1_5-2vcpu-16gb-intel"
    G_4VCPU_16GB_INTEL = "g-4vcpu-16gb-intel"
    GD_4VCPU_16GB_INTEL = "gd-4vcpu-16gb-intel"
    SO1_5_2VCPU_16GB = "so1_5-2vcpu-16gb"
    S_8VCPU_32GB_AMD = "s-8vcpu-32gb-amd"
    M_4VCPU_32GB = "m-4vcpu-32gb"
    C_8 = "c-8"
    C2_8VCPU_16GB = "c2-8vcpu-16gb"
    S_8VCPU_32GB_640GB_INTEL = "s-8vcpu-32gb-640gb-intel"
    M_4VCPU_32GB_INTEL = "m-4vcpu-32gb-intel"
    M3_4VCPU_32GB = "m3-4vcpu-32gb"

    @staticmethod
    def list_cpu_optimized() -> list["MachineSize"]:
        all_sizes = list(MachineSize)
        return [s for s in all_sizes if s.name.startswith("C")]

    @staticmethod
    def list_with_matching_memory(gb_memory: int) -> list["MachineSize"]:
        all_sizes = list(MachineSize)
        out: list["MachineSize"] = []
        import re

        pattern = re.compile(r"\d+GB")
        for s in all_sizes:
            match = pattern.search(s.name)
            if match:
                memory = int(match.group()[:-2])
                if memory == gb_memory:
                    out.append(s)
        return out


def unit_test() -> None:
    cpu_optimized = MachineSize.list_cpu_optimized()
    print(cpu_optimized)

    gb_16 = MachineSize.list_with_matching_memory(16)
    print(gb_16)


if __name__ == "__main__":
    unit_test()
