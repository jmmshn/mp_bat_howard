from maggma.stores import MongoStore
import logging
from monty.serialization import MontyDecoder
import gridfs
import zlib
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with open('.:secrets:db_info.json') as json_file:
    db_login = json.load(json_file)
store1 = MongoStore("js_cathodes", "concat_electrodes_js",
                    host=db_login['host'],
                    username=db_login['username'],
                    password=db_login['password'],
                    )
store1.connect()
store2 = MongoStore("js_cathodes", "materials_js",
                    host=db_login['host'],
                    username=db_login['username'],
                    password=db_login['password'],
                    )
store2.connect()
store3 = MongoStore("js_cathodes", "tasks",
                    host=db_login['host'],
                    username=db_login['username'],
                    password=db_login['password'],
                    )
store3.connect()

class chgden_fetcher:
    def __init__(self, battid):
        self.battid = battid

    def get_task_id(self, battid):
        all_entries = store1.collection.find({'working_ion': 'Li', 'battid': battid})
        mat_ids = []
        for i in all_entries:
            mat_ids.extend(i['material_ids'])

        no_li_entries = store2.collection.find({'task_ids': {'$in': mat_ids}, 'elements': {'$nin': ['Li']}})
        no_li_ids = []
        for i in no_li_entries:
            no_li_ids.extend(i['task_ids'])

        contain_fs_id_list = store3.collection.find(
            {'task_id': {'$in': no_li_ids}, 'calcs_reversed.0.aeccar0_fs_id': {'$exists': True}})
        cc_task_ids = []
        for i in contain_fs_id_list:
            cc_task_ids.append(i['task_id'])

        return cc_task_ids[0]

    def get_aeccar_from_store(self):
        """
        Read the AECCAR grid_fs data into a Chgcar object
        :param tstore: MongoStore for the tasks database
        :param task_id: The id of the material entry
        :return: pymatgen Chrgcar object
        """
        task_id=self.get_task_id(self.battid)
        tstore=store3
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