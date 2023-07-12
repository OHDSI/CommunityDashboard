import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NetworkStudiesComponent } from './network-studies.component';

describe('NetworkStudiesComponent', () => {
  let component: NetworkStudiesComponent;
  let fixture: ComponentFixture<NetworkStudiesComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [NetworkStudiesComponent]
    });
    fixture = TestBed.createComponent(NetworkStudiesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
