#![feature(generic_arg_infer)]

use bluer::{
    gatt::remote::{Characteristic, Descriptor, Service},
    Adapter, Address, Device, Uuid,
};
use input::TourboxInput;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

const DEVICE_ADDR: bluer::Address = bluer::Address::new([0xDE, 0x85, 0xF6, 0xD0, 0xB1, 0xF2]);
const UUID_TOURBOX_SERVICE: Uuid = Uuid::from_u128(0xfff000001000800000805f9b34fb);
const UUID_CHAR0011: Uuid = Uuid::from_u128(0xfff300001000800000805f9b34fb);
const UUID_CHAR0011_DESC0013: Uuid = Uuid::from_u128(0x290200001000800000805f9b34fb);
const UUID_CHAR000F: Uuid = Uuid::from_u128(0xfff200001000800000805f9b34fb);
const UUID_CHAR000C: Uuid = Uuid::from_u128(0xfff100001000800000805f9b34fb);
const UUID_CHAR000C_DESC000E: Uuid = Uuid::from_u128(0x290200001000800000805f9b34fb);

mod input;

pub struct Tourbox {
    pub device: Device,
    pub service: Service,
    pub char0011: Characteristic,
    pub char0011_desc0013: Descriptor,
    pub char000f: Characteristic,
    pub char000c: Characteristic,
    pub char000c_desc000e: Descriptor,
}

impl Tourbox {
    pub async fn new(addr: Address, adapter: Adapter) -> Tourbox {
        let device = adapter.device(addr).unwrap();
        device.connect().await.unwrap();
        let service = find_service(&device, UUID_TOURBOX_SERVICE).await;
        let char0011 = find_characteristic(&service, UUID_CHAR0011).await;
        let char0011_desc0013 = find_descriptor(&char0011, UUID_CHAR0011_DESC0013).await;
        let char000f = find_characteristic(&service, UUID_CHAR000F).await;
        let char000c = find_characteristic(&service, UUID_CHAR000C).await;
        let char000c_desc000e = find_descriptor(&char000c, UUID_CHAR000C_DESC000E).await;

        return Tourbox {
            device,
            service,
            char0011,
            char0011_desc0013,
            char000f,
            char000c,
            char000c_desc000e,
        };
    }
    pub async fn initial_protocol(&mut self) -> bluer::Result<()> {
        let mut writer = self.char000f.write_io().await?;
        let line_1: [u8; _] = [0x55, 0x00, 0x07, 0x88, 0x94, 0x00, 0x1a, 0xfe];
        let line_2: [u8; _] = [
            0xb5, 0x00, 0x5d, 0x04, 0x08, 0x05, 0x08, 0x06, 0x08, 0x07, 0x08, 0x08, 0x08, 0x09,
            0x08, 0x0b, 0x08, 0x0c, 0x08, 0x0d,
        ];
        let line_3: [u8; _] = [
            0x08, 0x0e, 0x08, 0x0f, 0x08, 0x26, 0x08, 0x27, 0x08, 0x28, 0x08, 0x29, 0x08, 0x3b,
            0x08, 0x3c, 0x08, 0x3d, 0x08, 0x3e,
        ];
        let line_4: [u8; _] = [
            0x08, 0x3f, 0x08, 0x40, 0x08, 0x41, 0x08, 0x42, 0x08, 0x43, 0x08, 0x44, 0x08, 0x45,
            0x08, 0x46, 0x08, 0x47, 0x08, 0x48,
        ];
        let line_5: [u8; _] = [
            0x08, 0x49, 0x08, 0x4a, 0x08, 0x4b, 0x08, 0x4c, 0x08, 0x4d, 0x08, 0x4e, 0x08, 0x4f,
            0x08, 0x50, 0x08, 0x51, 0x08, 0x52,
        ];
        let line_6: [u8; _] = [
            0x08, 0x53, 0x08, 0x54, 0x08, 0xa8, 0x08, 0xa9, 0x08, 0xaa, 0x08, 0xab, 0x08, 0xfe,
        ];
        writer.write_all(&line_1).await?;
        writer.write_all(&line_2).await?;
        writer.write_all(&line_3).await?;
        writer.write_all(&line_4).await?;
        writer.write_all(&line_5).await?;
        writer.write_all(&line_6).await?;
        println!("initial protocol completed");
        Ok(())
    }
    pub async fn notifications(&mut self) -> bluer::Result<()> {
        let mut notifier = self.char000c.notify_io().await?;
        let mut buffer = [0u8; 2];
        loop {
            let amount = notifier.read(&mut buffer).await?;
            let event = if amount == 1 {
                TourboxInput::from_u8(buffer[0])
            } else if amount == 2 {
                TourboxInput::from_u16(u16::from_be_bytes(buffer))
            } else {
                panic!()
            };
            println!("Got {event}");
        }
    }
}

async fn find_service(device: &Device, uuid: Uuid) -> Service {
    for service in device.services().await.unwrap() {
        if service.uuid().await.unwrap() == uuid {
            return service;
        }
    }
    panic!("Service not found! {}", uuid);
}

async fn find_characteristic(service: &Service, uuid: Uuid) -> Characteristic {
    for characteristic in service.characteristics().await.unwrap() {
        if characteristic.uuid().await.unwrap() == uuid {
            return characteristic;
        }
    }
    panic!("Characteristic not found! {}", uuid);
}

async fn find_descriptor(characteristic: &Characteristic, uuid: Uuid) -> Descriptor {
    for descriptor in characteristic.descriptors().await.unwrap() {
        if descriptor.uuid().await.unwrap() == uuid {
            return descriptor;
        }
    }
    panic!("Descriptor not found! {}", uuid);
}

#[tokio::main]
async fn main() -> bluer::Result<()> {
    let session = bluer::Session::new().await?;
    let adapter = session.default_adapter().await?;
    adapter.set_powered(true).await?;

    let mut tb = Tourbox::new(DEVICE_ADDR, adapter).await;
    println!("Device connected! :)");
    tb.initial_protocol().await?;
    tb.notifications().await?;

    Ok(())
}
