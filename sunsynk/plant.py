from sunsynk.resource import Resource, to_datetime, to_isoformat


class Plant(Resource):
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.thumb_url = data.get('thumbUrl')
        self.status = data.get('status')
        self.address = data.get('address')
        self.pac = data.get('pac')
        self.efficiency = data.get('efficiency')
        self.generation_today = data.get('etoday')
        self.generation_total = data.get('etotal')
        self.updated_at = to_datetime(data.get('updateAt'), "%Y-%m-%dT%H:%M:%SZ")
        self.created_at = to_isoformat(data.get('createAt'))
        self.type = data.get('type')
        self.master_id = data.get('masterId')
        self.share = data.get('share')
        self.plant_permissions = data.get('plantPermission')
        self.exist_camera = data.get('existCamera')
