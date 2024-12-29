import tarfile
import os

def compress_files_to_tar_gz(output_filename, file_paths):
    """
    Compresses the given files and files in directories into a tar.gz archive without foldering.

    Parameters:
        output_filename (str): Name of the output tar.gz file.
        file_paths (list): List of file paths or directories to be compressed.
    """
    with tarfile.open(output_filename, "w:gz") as tar:
        for path in file_paths:
            if os.path.isfile(path):
                # Add each file to the archive with its basename (no directory structure)
                tar.add(path, arcname=os.path.basename(path))
            elif os.path.isdir(path):
                # Add files from the directory without foldering
                tar.add(path, arcname=os.path.basename(path))

            else:
                print(f"Skipping {path}: Not a valid file or directory")

if __name__ == "__main__":
    # Example usage

    paths_to_compress = ["./docs/_build", "MyCovertChannel.py", "README.md", "config.json"]
    output_tar_gz = "78.tar.gz"

    compress_files_to_tar_gz(output_tar_gz, paths_to_compress)

    print(f"Files and folders compressed into {output_tar_gz}")
