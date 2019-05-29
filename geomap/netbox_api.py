import pynetbox
from django.db.models import Q
from .helper_functions import card_bay_number

netbox_token = '1KvUok=bOT@%R6nH(7lG0*hfcXDFCrys-iYmgja9'
nb = pynetbox.api('http://10.0.0.225:8000', token=netbox_token)

def create_site(property):
    site = nb.dcim.sites.get(name=property.name)
    if not site:
        try:
            region = nb.dcim.regions.get(name=property.market)
            if not region:
                region = nb.dcim.regions.create(name=property.market, slug=property.market)
            site = nb.dcim.sites.create(region=region.id, name=property.name, slug=property.slug, physical_address=property.address, status=2)
        except:
            return False
        return site.id
    return False

def get_device_types(tags=[]):
    if not type(tags) == list:
        return []

    eq_list = [(None, '---------')]
    try:
        for tag in tags:
            eq_list = eq_list + [(dt.model, dt.model) for dt in nb.dcim.device_types.filter(tag=tag)]
    except:
        pass

    return eq_list

def get_tags_of_device(model):
    eq_list = nb.dcim.device_types.get(model=model)
    if eq_list:
        return eq_list.tags
    return []

def get_dt_with_tag(tags):
    dtl = []
    if not type(tags) == list:
        return dtl
    for tag in tags:
        print(tag)
        dt = nb.dcim.device_types.filter(tag=tag.lower())
        if dt and not dtl:
            dtl = dt
        elif dt:
            n_dtl = []
            for i in dtl:
                for j in dt:
                    if i.model == j.model:
                        n_dtl.append(i)
            dtl = n_dtl
    return dtl

def create_racks(property):
    tags = get_tags_of_device(property.equipment)

    if 'router' in tags:
        router_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-router-rack1' % (property.slug,), status=2,
                                           u_height=45)
        gpon_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-gpon-rack1' % (property.slug,), status=2,
                                         u_height=45)
        switch_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-switch-rack1' % (property.slug,), status=2,
                                           u_height=45)
    if 'switch' in tags and not property.gpon_feed:
        gpon_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-gpon-rack1' % (property.slug,), status=2,
                                         u_height=45)
        switch_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-switch-rack1' % (property.slug,), status=2,
                                           u_height=45)
    if 'switch' in tags and property.gpon_feed:
        switch_rack = nb.dcim.racks.create(site=property.netbox_id, name='%s-switch-rack1' % (property.slug,), status=2,
                                           u_height=45)

def create_vlans(prop):
    tags = get_tags_of_device(prop.equipment)

    if 'router' in tags:
        nb.ipam.vlans.create(site=prop.netbox_id, vid=200, name=prop.hostname + '-MGNT', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=450, name=prop.hostname + '-IPTV', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=500, name=prop.hostname + '-DATA', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=699, name=prop.hostname + '-WIFI-CCR1-WAN', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=700, name=prop.hostname + '-WIFI-CCR2-WAN', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=701, name=prop.hostname + '-CCR', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=750, name=prop.hostname + '-WAP-MGNT', status=2)
    if 'switch' in tags:
        feed = prop.feeds.all()[0]

        feeding_of_feed = feed.feeding.filter(~Q(pk=prop.pk))

        ip_tv = 451
        data = 501
        ccr = 702
        ap_mgnt = 752

        if feeding_of_feed:
            for prop1 in feeding_of_feed:
                vlans = nb.ipam.vlans.filter(site_id=prop1.netbox_id)
                for vlan in vlans:

                    if int(str(vlan.vid)[:1]) == 4 and vlan.vid >= ip_tv:
                        ip_tv = vlan.vid + 1
                    elif int(str(vlan.vid)[:1]) == 5 and vlan.vid >= data:
                        data = vlan.vid + 1
                    if int(str(vlan.vid)[:2]) == 75 and vlan.vid >= ap_mgnt:
                        ap_mgnt = vlan.vid + 1
                    if int(str(vlan.vid)[:2]) == 70 and vlan.vid >= ccr:
                        ccr = vlan.vid + 1

        nb.ipam.vlans.create(site=prop.netbox_id, vid=ip_tv, name=prop.hostname + '-IPTV', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=data, name=prop.hostname + '-DATA', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=ccr, name=prop.hostname + '-CCR', status=2)
        nb.ipam.vlans.create(site=prop.netbox_id, vid=ap_mgnt, name=prop.hostname + '-WAP-MGNT', status=2)

def add_card_to(router, card, cpu=False):
    if card.parent_device:
        return None
    bays = nb.dcim.device_bays.filter(device_id=router.id)
    for bay in bays:
        if not cpu and 'RSP' not in bay.name and not bay.installed_device:
            bay_num = card_bay_number(bay.name)

            card_int = nb.dcim.interfaces.filter(device_id=card.id)

            for int in card_int:
                name_list = int.name.split('/')
                name_list[1] = bay_num
                int_name = '/'.join(name_list)
                nb.dcim.interfaces.create(device=router.id, name=int_name)
            bay.installed_device = card
            bay.save()
            break
        elif cpu and 'RSP' in bay.name and not bay.installed_device:
            bay.installed_device = card
            bay.save()
            break
    return None

def create_device(prop):
    tags = get_tags_of_device(prop.equipment)

    if 'router' in tags:
        device_type = nb.dcim.device_types.get(model=prop.equipment)
        dr = nb.dcim.device_roles.get(name='Router')
        if not dr:
            dr = nb.dcim.device_roles.create(name='Router', slug='router', color='3f51b5')
        router = nb.dcim.devices.create(name=prop.hostname + '-MDF-RTR1', device_type=device_type.id, site=prop.netbox_id, device_role=dr.id, status=2)

        card_type = get_dt_with_tag([device_type.model, 'card'])
        if card_type:
            card_type = card_type[0]

            card1 = nb.dcim.devices.create(device_type=card_type.id, site=prop.netbox_id, device_role=5, status=2)
            add_card_to(router, card1)

            card2 = nb.dcim.devices.create(device_type=card_type.id, site=prop.netbox_id, device_role=5, status=2)
            add_card_to(router, card2)

        cpu_type = get_dt_with_tag([device_type.model, 'cpu'])
        if cpu_type:
            cpu_type = cpu_type[0]

            processor1 = nb.dcim.devices.create(device_type=cpu_type.id, site=prop.netbox_id, device_role=6, status=2)
            add_card_to(router, processor1, cpu=True)

            processor2 = nb.dcim.devices.create(device_type=cpu_type.id, site=prop.netbox_id, device_role=6, status=2)
            add_card_to(router, processor2, cpu=True)

        device_type = nb.dcim.device_types.get(model='WS-C2960X-24PS-L')
        dr = nb.dcim.device_roles.get(name='Switch')
        if not dr:
            dr = nb.dcim.device_roles.create(name='Switch', slug='switch', color='ffc107')
        nb.dcim.devices.create(name=prop.hostname + '-MDF-SW1', device_type=device_type.id,
                                        site=prop.netbox_id, device_role=dr.id, status=2)

        if not prop.gpon_feed:
            device_type = nb.dcim.device_types.get(model='7360 ISAM FX')
            dr = nb.dcim.device_roles.get(name='GPON')
            if not dr:
                dr = nb.dcim.device_roles.create(name='Switch', slug='switch', color='ffc107')
            nb.dcim.devices.create(name=prop.hostname + '-MDF-GPON1', device_type=device_type.id,
                                            site=prop.netbox_id, device_role=dr.id, status=2)


def delete_components(prop):
    if prop.netbox_id:
        [prefix.delete() for prefix in nb.ipam.prefixes.filter(site_id=prop.netbox_id)]
        [vlan.delete() for vlan in nb.ipam.vlans.filter(site_id=prop.netbox_id)]
        [device.delete() for device in nb.dcim.devices.filter(site_id=prop.netbox_id)]
        [rack.delete() for rack in nb.dcim.racks.filter(site_id=prop.netbox_id)]

def delete_site(prop):
    delete_components(prop)
    site = nb.dcim.sites.get(name=prop.name)
    if site:
        site.delete()

def get_prefix_for(prop, name):
    role = nb.ipam.roles.get(name=name)
    if not role:
        role = nb.ipam.roles.create(name=name, slug=name.lower())
    return nb.ipam.prefixes.get(site_id=prop.netbox_id, role_id=role.id)

def set_prefix_for(prop, name, prefix):
    role = nb.ipam.roles.get(name=name)
    if not role:
        role = nb.ipam.roles.create(name=name, slug=name.lower())
    return nb.ipam.prefixes.create(site_id=prop.id, role_id=role.id, prefix=prefix)