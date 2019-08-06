import gridfs
import zlib
import json
from pymatgen import MontyDecoder

def get_aeccar_from_store(tstore, task_id):
    """
    Read the AECCAR grid_fs data into a Chgcar object
    :param tstore: MongoStore for the tasks database
    :param task_id: The id of the material entry
    :return: pymatgen Chrgcar object
    """
    tstore.connect()
    m_task = tstore.query_one({'task_id': task_id})
    try:
        fs_id = m_task['calcs_reversed'][0]['aeccar0_fs_id']
    except:
        logger.info('AECCAR0 Missing from task #'.format(task_id))
        return None

    fs = gridfs.GridFS(tstore.collection.database, 'aeccar0_fs')
    chgcar_json = zlib.decompress(fs.get(fs_id).read())
    aeccar0 = json.loads(chgcar_json, cls=MontyDecoder)

    try:
        fs_id = m_task['calcs_reversed'][0]['aeccar2_fs_id']
    except:
        logger.info('AECCAR2 Missing from task #'.format(task_id))
        return None

    fs = gridfs.GridFS(tstore.collection.database, 'aeccar2_fs')
    chgcar_json = zlib.decompress(fs.get(fs_id).read())
    aeccar2 = json.loads(chgcar_json, cls=MontyDecoder)

    return aeccar0 + aeccar2
